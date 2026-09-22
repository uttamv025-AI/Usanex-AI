from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.schemas.auth import (
    LoginRequest,
    RegisterOTPRequest,
    RegisterVerifyRequest,
    ForgotOTPRequest,
    ForgotVerifyRequest,
    ResetPasswordRequest,
)
from backend.services.auth_service import (
    login_user,
    request_register_otp,
    verify_registration,
    request_forgot_otp,
    verify_forgot_otp,
    reset_password,
)


router = APIRouter()


# =========================================================
# DATABASE DEPENDENCY
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# LOGIN
# =========================================================

@router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    return login_user(
        db=db,
        identifier=request.identifier,
        password=request.password,
    )


# =========================================================
# REGISTER - REQUEST OTP
# =========================================================

@router.post("/register/request-otp")
async def register_request_otp(
    request: RegisterOTPRequest,
    db: Session = Depends(get_db),
):
    return request_register_otp(
        db=db,
        name=request.name,
        mobile=request.mobile,
        password=request.password,
    )


# =========================================================
# REGISTER - VERIFY OTP
# =========================================================

@router.post("/register/verify-otp")
async def register_verify_otp(
    request: RegisterVerifyRequest,
    db: Session = Depends(get_db),
):
    return verify_registration(
        db=db,
        name=request.name,
        mobile=request.mobile,
        password=request.password,
        otp=request.otp,
    )


# =========================================================
# FORGOT PASSWORD - REQUEST OTP
# =========================================================

@router.post("/forgot-password/request-otp")
async def forgot_password_request_otp(
    request: ForgotOTPRequest,
    db: Session = Depends(get_db),
):
    return request_forgot_otp(
        db=db,
        identifier=request.identifier,
    )


# =========================================================
# FORGOT PASSWORD - VERIFY OTP
# =========================================================

@router.post("/forgot-password/verify-otp")
async def forgot_password_verify_otp(
    request: ForgotVerifyRequest,
    db: Session = Depends(get_db),
):
    return verify_forgot_otp(
        db=db,
        identifier=request.identifier,
        otp=request.otp,
    )


# =========================================================
# RESET PASSWORD
# =========================================================

@router.post("/forgot-password/reset-password")
async def forgot_password_reset(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return reset_password(
        db=db,
        identifier=request.identifier,
        new_password=request.new_password,
        confirm_password=request.confirm_password,
    )
