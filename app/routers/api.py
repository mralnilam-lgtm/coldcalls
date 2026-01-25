"""
API Router - JSON endpoints for AJAX calls and TwiML
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign, CampaignNumber, CallerID, Country, Audio, CampaignStatus
from app.schemas import DashboardStats, CampaignProgress, DropdownCallerID, DropdownCountry, DropdownAudio

router = APIRouter(prefix="/api", tags=["api"])


# ============== TwiML Endpoint ==============

@router.post("/twiml/{campaign_id}")
async def twiml_handler(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Dynamic TwiML endpoint for handling calls with machine detection.

    Twilio calls this URL when the call is answered.
    - If human: Transfer to the campaign's 3CX number
    - If machine: Hang up

    Twilio sends AnsweredBy parameter:
    - human
    - machine_start, machine_end_beep, machine_end_silence, machine_end_other
    - fax
    - unknown
    """
    # Parse form data from Twilio
    form_data = await request.form()
    answered_by = form_data.get("AnsweredBy", "unknown")
    caller_id = form_data.get("From", "")  # Original caller ID (the number we called)

    # Get campaign
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        # Return hangup if campaign not found
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
        return Response(content=twiml, media_type="application/xml")

    # Get transfer number from user settings
    transfer_number = campaign.user.transfer_number

    if not transfer_number:
        # No transfer number configured - hang up
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
        return Response(content=twiml, media_type="application/xml")

    # Check if answered by human
    if answered_by == "human":
        # Transfer to 3CX number, preserving the original caller ID
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial callerId="{campaign.caller_id.phone_number}" timeout="30">
        <Number>{transfer_number}</Number>
    </Dial>
</Response>'''
    else:
        # Machine/voicemail detected - hang up
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'

    return Response(content=twiml, media_type="application/xml")


@router.post("/twiml/{campaign_id}/play")
async def twiml_play_audio(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    TwiML endpoint that plays the campaign audio.
    Used as the initial URL when making the call.
    After playing, Twilio will check AnsweredBy and call the main handler.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
        return Response(content=twiml, media_type="application/xml")

    # Get transfer number from user settings
    transfer_number = campaign.user.transfer_number

    if not transfer_number:
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
        return Response(content=twiml, media_type="application/xml")

    # Play audio then transfer if human
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{campaign.audio.r2_url}</Play>
    <Dial callerId="{campaign.caller_id.phone_number}" timeout="30">
        <Number>{transfer_number}</Number>
    </Dial>
</Response>'''

    return Response(content=twiml, media_type="application/xml")


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).all()

    return DashboardStats(
        credits=user.credits,
        total_campaigns=len(campaigns),
        active_campaigns=len([c for c in campaigns if c.status == CampaignStatus.RUNNING]),
        total_calls=sum(c.processed_numbers for c in campaigns),
        successful_calls=sum(c.successful_calls for c in campaigns),
        total_spent=sum(c.total_cost for c in campaigns)
    )


@router.get("/campaigns/{campaign_id}/progress", response_model=CampaignProgress)
async def get_campaign_progress(
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get campaign progress for real-time updates"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignProgress(
        status=campaign.status,
        total=campaign.total_numbers,
        processed=campaign.processed_numbers,
        successful=campaign.successful_calls,
        failed=campaign.failed_calls,
        cost=campaign.total_cost,
        progress_percent=campaign.progress_percent
    )


@router.get("/campaigns/{campaign_id}/numbers")
async def get_campaign_numbers(
    campaign_id: int,
    page: int = 1,
    per_page: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of campaign numbers"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    offset = (page - 1) * per_page
    numbers = db.query(CampaignNumber).filter(
        CampaignNumber.campaign_id == campaign_id
    ).order_by(CampaignNumber.id).offset(offset).limit(per_page).all()

    total = db.query(CampaignNumber).filter(
        CampaignNumber.campaign_id == campaign_id
    ).count()

    return {
        "numbers": [
            {
                "id": n.id,
                "phone_number": n.phone_number,
                "status": n.status.value,
                "duration_seconds": n.duration_seconds,
                "cost": n.cost,
                "answered_by": n.answered_by,
                "processed_at": n.processed_at.isoformat() if n.processed_at else None
            }
            for n in numbers
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


# ============== Dropdown Data ==============

@router.get("/data/caller-ids", response_model=list[DropdownCallerID])
async def get_caller_ids(
    country: str = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active caller IDs, optionally filtered by country"""
    query = db.query(CallerID).filter(CallerID.is_active == True)

    if country:
        query = query.filter(CallerID.country_code == country.upper())

    return query.order_by(CallerID.phone_number).all()


@router.get("/data/countries", response_model=list[DropdownCountry])
async def get_countries(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active countries"""
    return db.query(Country).filter(
        Country.is_active == True
    ).order_by(Country.name).all()


@router.get("/data/audios", response_model=list[DropdownAudio])
async def get_audios(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active audios"""
    return db.query(Audio).filter(
        Audio.is_active == True
    ).order_by(Audio.name).all()
