"""
API Router - JSON endpoints for AJAX calls
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign, CampaignNumber, CallerID, Country, Audio, CampaignStatus
from app.schemas import DashboardStats, CampaignProgress, DropdownCallerID, DropdownCountry, DropdownAudio

router = APIRouter(prefix="/api", tags=["api"])


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
