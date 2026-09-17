# ============================================================
# USANEX - SERVER
# FastAPI + PostgreSQL + Argon2
# ============================================================

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from datetime import datetime, timedelta
import secrets
import os


# ============================================================
# DATABASE IMPORT
# ============================================================

from database import (
    SessionLocal,
    User,
    OTPVerification,
    Connection,
)


# ============================================================
# APP
# ============================================================

app = FastAPI(title="Usanex")


password_hasher = PasswordHasher()


# ============================================================
# DATABASE SESSION
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# REQUEST MODELS
# ============================================================

class LoginRequest(BaseModel):
    mobile: str
    password: str


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

    old_rows = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == identifier,
            OTPVerification.purpose == purpose
        )
        .all()
    )

    for item in old_rows:
        db.delete(item)

    row = OTPVerification(
        identifier=identifier,
        otp=otp,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=2),
        verified=False
    )

    db.add(row)
    db.commit()

    return otp


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    identifier = request.mobile.strip()
    password = request.password

    if not identifier or not password:

        return {
            "ok": False,
            "message": "Mobile number/username and password are required"
        }

    # Login using mobile OR user_id
    user = (
        db.query(User)
        .filter(
            (User.mobile == identifier) |
            (User.user_id == identifier)
        )
        .first()
    )

    if not user:

        return {
            "ok": False,
            "message": "Invalid username/mobile or password"
        }

    try:

        password_hasher.verify(
            user.password_hash,
            password
        )

    except (
        VerifyMismatchError,
        VerificationError
    ):

        return {
            "ok": False,
            "message": "Invalid username/mobile or password"
        }

    token = secrets.token_urlsafe(32)

    return {

        "ok": True,

        "message": "Login successful",

        "token": token,

        "user": {

            "user_id": user.user_id,

            "name": user.name,

            "mobile": user.mobile

        }
    }


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

    if not name or not mobile or not password:

        return {
            "ok": False,
            "message": "Please fill all fields"
        }

    if not mobile.isdigit() or len(mobile) != 10:

        return {
            "ok": False,
            "message": "Enter a valid 10-digit mobile number"
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

    name = request.name.strip()
    mobile = request.mobile.strip()
    password = request.password
    otp = request.otp.strip()

    if not name or not mobile or not password or not otp:

        return {
            "ok": False,
            "message": "All fields are required"
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == mobile,
            OTPVerification.purpose == "register",
            OTPVerification.verified == False
        )
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message": "OTP not found. Please request a new OTP"
        }

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)
        db.commit()

        return {
            "ok": False,
            "message": "OTP expired. Please request a new OTP"
        }

    if verification.otp != otp:

        return {
            "ok": False,
            "message": "Invalid OTP"
        }

    # Check again before creating user
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

    # Generate unique user ID
    while True:

        generated_user_id = (
            "UX" +
            secrets.token_hex(5)
        )

        exists = (
            db.query(User)
            .filter(
                User.user_id == generated_user_id
            )
            .first()
        )

        if not exists:
            break

    new_user = User(

        user_id=generated_user_id,

        name=name,

        mobile=mobile,

        password_hash=password_hasher.hash(
            password
        )
    )

    db.add(new_user)

    verification.verified = True

    try:

        db.commit()

    except IntegrityError:

        db.rollback()

        return {
            "ok": False,
            "message": "Registration failed. Please try again"
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
            "message": "Enter username or mobile number"
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
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message": "OTP not found. Please request a new OTP"
        }

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)
        db.commit()

        return {
            "ok": False,
            "message": "OTP expired. Please request a new OTP"
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
# FORGOT PASSWORD - RESET PASSWORD
# ============================================================

@app.post("/forgot-password/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):

    identifier = request.identifier.strip()

    new_password = request.new_password

    confirm_password = request.confirm_password

    if len(new_password) < 6:

        return {
            "ok": False,
            "message": "Password must be at least 6 characters"
        }

    if new_password != confirm_password:

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
        .order_by(
            OTPVerification.id.desc()
        )
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

    user.password_hash = (
        password_hasher.hash(
            new_password
        )
    )

    verification.verified = False

    db.commit()

    return {

        "ok": True,

        "message": "Password changed successfully"
    }


# ============================================================
# GET CONNECTED PEOPLE
# ============================================================

@app.get("/api/connections")
async def get_connections(
    user_id: str,
    db: Session = Depends(get_db)
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": False,
            "message": "user_id is required",
            "connections": []
        }

    # Find all connection rows
    rows = (
        db.query(Connection)
        .filter(
            (Connection.user_a_id == user_id) |
            (Connection.user_b_id == user_id)
        )
        .all()
    )

    connected_ids = []

    for row in rows:

        if row.user_a_id == user_id:

            connected_ids.append(
                row.user_b_id
            )

        elif row.user_b_id == user_id:

            connected_ids.append(
                row.user_a_id
            )

    # Remove duplicate IDs
    connected_ids = list(
        dict.fromkeys(
            connected_ids
        )
    )

    if not connected_ids:

        return {

            "ok": True,

            "connections": []
        }

    users = (
        db.query(User)
        .filter(
            User.user_id.in_(connected_ids)
        )
        .all()
    )

    result = []

    for user in users:

        result.append({

            "user_id": user.user_id,

            "name": user.name,

            # Current database column
            "profile_photo": user.profile_photo,

            # Home page compatibility
            "profile_picture": user.profile_photo,

            "username": user.user_id
        })

    return {

        "ok": True,

        "connections": result
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {

        "ok": True,

        "status": "online",

        "app": "Usanex"
    }


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def home():

    return FileResponse(
        "index.html"
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.getenv(
            "PORT",
            "8000"
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
