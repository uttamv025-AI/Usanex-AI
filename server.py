from fastapi import FastAPI, Depends
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from argon2 import PasswordHasher
from datetime import datetime, timedelta
import secrets
import uuid
import os

from database import SessionLocal, User, OTPVerification


app = FastAPI(title="Usanex AI")

password_hasher = PasswordHasher()


# ============================================================
# REQUEST MODELS
# ============================================================

class RegisterOTPRequest(BaseModel):
    name: str
    mobile: str
    password: str


class RegisterVerifyRequest(BaseModel):
    name: str
    mobile: str
    password: str
    otp: str


class ForgotOTPRequest(BaseModel):
    identifier: str


class ForgotVerifyRequest(BaseModel):
    identifier: str
    otp: str


class ResetPasswordRequest(BaseModel):
    identifier: str
    new_password: str
    confirm_password: str


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# OTP
# ============================================================

def generate_otp():
    return str(secrets.randbelow(900000) + 100000)


def save_otp(
    db: Session,
    identifier: str,
    purpose: str
):
    otp = generate_otp()

    old_otps = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == identifier,
            OTPVerification.purpose == purpose
        )
        .all()
    )

    for old in old_otps:
        db.delete(old)

    new_otp = OTPVerification(
        identifier=identifier,
        otp=otp,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=2),
        verified=False
    )

    db.add(new_otp)
    db.commit()

    return otp


# ============================================================
# REGISTER - REQUEST OTP
# ============================================================

@app.post("/register/request-otp")
async def register_request_otp(
    request: RegisterOTPRequest,
    db: Session = Depends(get_db)
):
    name = request.name.strip()
    mobile = request.mobile.strip()
    password = request.password

    if not name:
        return {
            "ok": False,
            "message": "Name is required"
        }

    if not mobile:
        return {
            "ok": False,
            "message": "Mobile number is required"
        }

    if len(password) < 6:
        return {
            "ok": False,
            "message": "Password must be at least 6 characters"
        }

    existing_user = (
        db.query(User)
        .filter(User.mobile == mobile)
        .first()
    )

    if existing_user:
        return {
            "ok": False,
            "message": "Mobile number already registered"
        }

    otp = save_otp(
        db,
        mobile,
        "register"
    )

    return {
        "ok": True,
        "message": "OTP generated",
        "otp": otp,
        "expires_in": 120
    }


# ============================================================
# REGISTER - VERIFY OTP
# ============================================================

@app.post("/register/verify-otp")
async def register_verify_otp(
    request: RegisterVerifyRequest,
    db: Session = Depends(get_db)
):
    mobile = request.mobile.strip()
    otp = request.otp.strip()

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == mobile,
            OTPVerification.purpose == "register",
            OTPVerification.verified == False
        )
        .order_by(OTPVerification.id.desc())
        .first()
    )

    if not verification:
        return {
            "ok": False,
            "message": "OTP not found or already used"
        }

    if datetime.utcnow() > verification.expires_at:
        db.delete(verification)
        db.commit()

        return {
            "ok": False,
            "message": "OTP expired. Please request a new OTP."
        }

    if verification.otp != otp:
        return {
            "ok": False,
            "message": "Invalid OTP"
        }

    existing_user = (
        db.query(User)
        .filter(User.mobile == mobile)
        .first()
    )

    if existing_user:
        return {
            "ok": False,
            "message": "Mobile number already registered"
        }

    user_id = "UX" + uuid.uuid4().hex[:10]

    password_hash = password_hasher.hash(
        request.password
    )

    new_user = User(
        user_id=user_id,
        name=request.name.strip(),
        mobile=mobile,
        password_hash=password_hash
    )

    try:
        db.add(new_user)
        verification.verified = True

        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()

        return {
            "ok": False,
            "message": "Registration failed"
        }

    return {
        "ok": True,
        "message": "Registration successful",
        "user_id": new_user.user_id,
        "name": new_user.name,
        "mobile": new_user.mobile
    }


# ============================================================
# FORGOT PASSWORD - REQUEST OTP
# ============================================================

@app.post("/forgot-password/request-otp")
async def forgot_password_request_otp(
    request: ForgotOTPRequest,
    db: Session = Depends(get_db)
):
    identifier = request.identifier.strip()

    if not identifier:
        return {
            "ok": False,
            "message": "User ID or mobile number is required"
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier) |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return {
            "ok": False,
            "message": "User ID or mobile number not found"
        }

    otp = save_otp(
        db,
        user.mobile,
        "forgot_password"
    )

    return {
        "ok": True,
        "message": "OTP generated",
        "otp": otp,
        "expires_in": 120
    }


# ============================================================
# FORGOT PASSWORD - VERIFY OTP
# ============================================================

@app.post("/forgot-password/verify-otp")
async def forgot_password_verify_otp(
    request: ForgotVerifyRequest,
    db: Session = Depends(get_db)
):
    identifier = request.identifier.strip()
    otp = request.otp.strip()

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier) |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return {
            "ok": False,
            "message": "User not found"
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == user.mobile,
            OTPVerification.purpose == "forgot_password",
            OTPVerification.verified == False
        )
        .order_by(OTPVerification.id.desc())
        .first()
    )

    if not verification:
        return {
            "ok": False,
            "message": "OTP not found or already used"
        }

    if datetime.utcnow() > verification.expires_at:
        db.delete(verification)
        db.commit()

        return {
            "ok": False,
            "message": "OTP expired. Please request a new OTP."
        }

    if verification.otp != otp:
        return {
            "ok": False,
            "message": "Invalid OTP"
        }

    verification.verified = True
    db.commit()

    return {
        "ok": True,
        "message": "OTP verified"
    }


# ============================================================
# FORGOT PASSWORD - RESET
# ============================================================

@app.post("/forgot-password/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    identifier = request.identifier.strip()

    if len(request.new_password) < 6:
        return {
            "ok": False,
            "message": "Password must be at least 6 characters"
        }

    if request.new_password != request.confirm_password:
        return {
            "ok": False,
            "message": "Passwords do not match"
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier) |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return {
            "ok": False,
            "message": "User not found"
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == user.mobile,
            OTPVerification.purpose == "forgot_password",
            OTPVerification.verified == True
        )
        .order_by(OTPVerification.id.desc())
        .first()
    )

    if not verification:
        return {
            "ok": False,
            "message": "OTP verification required"
        }

    if datetime.utcnow() > verification.expires_at:
        verification.verified = False
        db.commit()

        return {
            "ok": False,
            "message": "OTP verification expired"
        }

    user.password_hash = password_hasher.hash(
        request.new_password
    )

    verification.verified = False

    db.commit()

    return {
        "ok": True,
        "message": "Password changed successfully"
    }


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def home():
    return FileResponse("index.html")


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    return {
        "ok": True,
        "status": "online",
        "app": "Usanex AI"
    }


# ============================================================
# LOCAL RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
