"""
Authentication Router - Login, Register, Logout
"""
from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    registered: bool = False,
    user: User = Depends(get_current_user_optional)
):
    """Display login page"""
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "registered": registered,
            "error": None
        }
    )


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process login form"""
    user = db.query(User).filter(User.email == email.lower()).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "Invalid email or password",
                "registered": False
            },
            status_code=400
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "Your account has been disabled",
                "registered": False
            },
            status_code=403
        )

    # Create JWT token
    token = create_access_token({"sub": str(user.id)})

    # Redirect to dashboard with token in cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.JWT_EXPIRATION_HOURS * 3600,
        samesite="lax"
    )

    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional)
):
    """Display registration page"""
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Check user limit
    user_count = db.query(User).filter(User.is_admin == False).count()
    registration_closed = user_count >= settings.MAX_USERS

    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "error": None,
            "registration_closed": registration_closed
        }
    )


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process registration form"""
    # Check user limit
    user_count = db.query(User).filter(User.is_admin == False).count()
    if user_count >= settings.MAX_USERS:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "Registration is closed - maximum users reached",
                "registration_closed": True
            },
            status_code=400
        )

    # Validate passwords match
    if password != password_confirm:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "Passwords do not match",
                "registration_closed": False
            },
            status_code=400
        )

    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "Password must be at least 6 characters",
                "registration_closed": False
            },
            status_code=400
        )

    # Check existing email
    email = email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "Email already registered",
                "registration_closed": False
            },
            status_code=400
        )

    # Create user
    user = User(
        email=email,
        password_hash=hash_password(password),
        is_admin=False,
        is_active=True
    )
    db.add(user)
    db.commit()

    return RedirectResponse(url="/auth/login?registered=true", status_code=302)


@router.get("/logout")
async def logout():
    """Logout user by clearing cookie"""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
