"""
Dashboard Router - User home page and settings
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from twilio.rest import Client as TwilioClient

from app.auth import encrypt_twilio_credentials
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign, CampaignStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Main dashboard page"""
    # Get recent campaigns
    campaigns = db.query(Campaign).filter(
        Campaign.user_id == user.id
    ).order_by(Campaign.created_at.desc()).limit(5).all()

    # Calculate stats
    all_campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).all()

    stats = {
        "credits": user.credits,
        "total_campaigns": len(all_campaigns),
        "active_campaigns": len([c for c in all_campaigns if c.status == CampaignStatus.RUNNING]),
        "total_calls": sum(c.processed_numbers for c in all_campaigns),
        "successful_calls": sum(c.successful_calls for c in all_campaigns),
        "total_spent": sum(c.total_cost for c in all_campaigns),
        "twilio_configured": user.twilio_configured
    }

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "campaigns": campaigns,
            "stats": stats
        }
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user: User = Depends(get_current_user),
    saved: bool = False,
    configure_twilio: bool = False
):
    """User settings page"""
    return templates.TemplateResponse(
        "dashboard/settings.html",
        {
            "request": request,
            "user": user,
            "saved": saved,
            "configure_twilio": configure_twilio,
            "error": None
        }
    )


@router.post("/settings/twilio")
async def save_twilio_credentials(
    request: Request,
    account_sid: str = Form(...),
    auth_token: str = Form(...),
    transfer_number: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save Twilio credentials and transfer number"""
    import re
    E164_PATTERN = re.compile(r'^\+[1-9]\d{1,14}$')

    # Validate transfer number
    transfer_number = transfer_number.strip()
    if not E164_PATTERN.match(transfer_number):
        return templates.TemplateResponse(
            "dashboard/settings.html",
            {
                "request": request,
                "user": user,
                "saved": False,
                "configure_twilio": False,
                "error": "Invalid transfer number. Use E.164 format (e.g., +15551234567)"
            },
            status_code=400
        )

    # Validate credentials by making a test API call
    try:
        client = TwilioClient(account_sid, auth_token)
        client.api.accounts(account_sid).fetch()
    except Exception as e:
        return templates.TemplateResponse(
            "dashboard/settings.html",
            {
                "request": request,
                "user": user,
                "saved": False,
                "configure_twilio": False,
                "error": f"Invalid Twilio credentials: {str(e)}"
            },
            status_code=400
        )

    # Encrypt and store
    user.twilio_account_sid_encrypted = encrypt_twilio_credentials(account_sid)
    user.twilio_auth_token_encrypted = encrypt_twilio_credentials(auth_token)
    user.transfer_number = transfer_number
    user.twilio_configured = True
    db.commit()

    return RedirectResponse(url="/dashboard/settings?saved=true", status_code=302)
