import secrets
import uuid
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from sqlalchemy.orm import Session

from backend.models import User, OTPVerification


password_hasher = PasswordHasher()


# =========================================================
# OTP
# =========================================================

def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)


def save_otp(
    db: Session,
    identifier: str,
    purpose: str,
) -> str:
    """
    Create a new OTP.

    Any previous OTP for the same identifier and purpose
    is removed before creating the new one.
    """

    old_otps = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == identifier,
            OTPVerification.purpose == purpose,
        )
        .all()
    )

    for old in old_otps:
        db.delete(old)

    otp = generate_otp()

    new_otp = OTPVerification(
        identifier=identifier,
        otp=otp,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=2),
        verified=False,
    )

    db.add(new_otp)
    db.commit()

    return otp


def verify_otp(
    db: Session,
    identifier: str,
    purpose: str,
    otp: str,
) -> bool:
    """Verify the latest unverified OTP."""

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == identifier,
            OTPVerification.purpose == purpose,
            OTPVerification.verified == False,
        )
        .order_by(OTPVerification.id.desc())
        .first()
    )

    if not verification:
        return False

    if verification.expires_at < datetime.utcnow():
        return False

    if verification.otp != otp:
        return False

    verification.verified = True
    db.commit()

    return True


# =========================================================
# LOGIN
# =========================================================

def login_user(
    db: Session,
    identifier: str,
    password: str,
):
    """Authenticate user using User ID or mobile number."""

    identifier = identifier.strip()

    if not identifier or not password:
        return {
            "ok": False,
            "message": "User ID/mobile and password are required",
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier)
            | (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return {
            "ok": False,
            "message": "Invalid User ID/mobile or password",
        }

    try:
        password_hasher.verify(
            user.password_hash,
            password,
        )
    except (VerifyMismatchError, VerificationError):
        return {
            "ok": False,
            "message": "Invalid User ID/mobile or password",
        }

    token = secrets.token_urlsafe(32)

    return {
        "ok": True,
        "message": "Login successful",
        "token": token,
        "user_id": user.user_id,
        "name": user.name,
        "mobile": user.mobile,
        "profile_photo": user.profile_photo,
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "mobile": user.mobile,
            "profile_photo": user.profile_photo,
        },
    }


# =========================================================
# REGISTER - REQUEST OTP
# =========================================================

def request_register_otp(
    db: Session,
    name: str,
    mobile: str,
    password: str,
):
    """Validate registration data and generate registration OTP."""

    name = name.strip()
    mobile = mobile.strip()

    if not name or not mobile or not password:
        return {
            "ok": False,
            "message": "Name, mobile and password are required",
        }

    if not mobile.isdigit() or len(mobile) != 10:
        return {
            "ok": False,
            "message": "Enter a valid 10-digit mobile number",
        }

    if len(password) < 6:
        return {
            "ok": False,
            "message": "Password must be at least 6 characters",
        }

    existing_user = (
        db.query(User)
        .filter(User.mobile == mobile)
        .first()
    )

    if existing_user:
        return {
            "ok": False,
            "message": "Mobile number is already registered",
        }

    otp = save_otp(
        db=db,
        identifier=mobile,
        purpose="register",
    )

    return {
        "ok": True,
        "message": "OTP generated",
        "otp": otp,
        "expires_in": 120,
    }


# =========================================================
# REGISTER - VERIFY OTP
# =========================================================

def verify_registration(
    db: Session,
    name: str,
    mobile: str,
    password: str,
    otp: str,
):
    """Verify registration OTP and create the user."""

    name = name.strip()
    mobile = mobile.strip()
    otp = otp.strip()

    if not name or not mobile or not password or not otp:
        return {
            "ok": False,
            "message": "All fields are required",
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == mobile,
            OTPVerification.purpose == "register",
            OTPVerification.verified == False,
        )
        .order_by(OTPVerification.id.desc())
        .first()
    )

    if not verification:
        return {
            "ok": False,
            "message": "OTP not found or already used",
        }

    if verification.expires_at < datetime.utcnow():
        return {
            "ok": False,
            "message": "OTP has expired",
        }

    if verification.otp != otp:
        return {
            "ok": False,
            "message": "Invalid OTP",
        }

    existing_user = (
        db.query(User)
        .filter(User.mobile == mobile)
        .first()
    )

    if existing_user:
        return {
            "ok": False,
            "message": "Mobile number is already registered",
        }

    user_id = "UX" + uuid.uuid4().hex[:10]

    password_hash = password_hasher.hash(password)

    user = User(
        user_id=user_id,
        name=name,
        mobile=mobile,
        password_hash=password_hash,
        profile_photo=None,
    )

    db.add(user)

    verification.verified = True

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()

        return {
            "ok": False,
            "message": "Registration failed",
        }

    return {
        "ok": True,
        "message": "Account created successfully",
        "user_id": user.user_id,
        "name": user.name,
        "mobile": user.mobile,
        "profile_photo": user.profile_photo,
    }


# =========================================================
# FORGOT PASSWORD - REQUEST OTP
# =========================================================

def request_forgot_otp(
    db: Session,
    identifier: str,
):
    """Find user by User ID/mobile and generate forgot-password OTP."""

    identifier = identifier.strip()

    if not identifier:
        return {
            "ok": False,
            "message": "User ID/mobile is required",
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier)
            | (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return {
            "ok": False,
            "message": "User not found",
        }

    otp = save_otp(
        db=db,
        identifier=user.mobile,
        purpose="forgot_password",
    )

    return {
        "ok": True,
        "message": "OTP generated",
        "otp": otp,
        "expires_in": 120,
    }


# =========================================================
# FORGOT PASSWORD - VERIFY OTP
# =========================================================

def verify_forgot_otp(
    db: Session,
    identifier: str,
    otp: str,
):
    """Verify forgot-password OTP."""

    identifier = identifier.strip()
    otp = otp.strip()

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier)
            | (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return {
            "ok": False,
            "message": "User not found",
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == user.mobile,
            OTPVerification.purpose == "forgot_password",
            OTPVerification.verified == False,
        )
        .order_by(OTPVerification.id.desc())
        .first()
    )

    if not verification:
        return {
            "ok": False,
            "message": "OTP not found or already used",
        }

    if verification.expires_at < datetime.utcnow():
        return {
            "ok": False,
            "message": "OTP has expired",
        }

    if verification.otp != otp:
        return {
            "ok": False,
            "message": "Invalid OTP",
        }

    verification.verified = True
    db.commit()

    return {
        "ok": True,
        "message": "OTP verified",
    }


# =========================================================
# RESET PASSWORD
# =========================================================

def reset_password(
    db: Session,
    identifier: str,
    new_password: str,
    confirm_password: str,
):
    """Reset password after successful forgot-password OTP verification."""

    identifier = identifier.strip()

    if len(new_password) < 6:
        return {
            "ok": False,
            "message": "Password must be at least 6 characters",
        }

    if new_password != confirm_password:
        return {
            "ok": False,
            "message": "Passwords do not match",
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier)
            | (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return {
            "ok": False,
            "message": "User not found",
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == user.mobile,
            OTPVerification.purpose == "forgot_password",
            OTPVerification.verified == True,
        )
        .order_by(OTPVerification.id.desc())
        .first()
    )

    if not verification:
        return {
            "ok": False,
            "message": "OTP verification required",
        }

    if verification.expires_at < datetime.utcnow():
        return {
            "ok": False,
            "message": "OTP verification has expired",
        }

    user.password_hash = password_hasher.hash(new_password)

    verification.verified = False

    db.commit()

    return {
        "ok": True,
        "message": "Password reset successfully",
}
