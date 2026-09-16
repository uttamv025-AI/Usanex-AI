from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError
)

from datetime import datetime, timedelta

import secrets
import uuid
import os


# ============================================================
# APP
# ============================================================

app = FastAPI(title="Usanex")

password_hasher = PasswordHasher()

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# REQUEST MODELS
# ============================================================

class LoginRequest(BaseModel):
    identifier: str
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
# FOLLOW REQUEST
# ============================================================

class FollowRequest(BaseModel):
    requester_user_id: str
    target_user_id: str


# ============================================================
# ACCEPT / REJECT
# ============================================================

class ConnectionActionRequest(BaseModel):
    notification_id: int
    user_id: str


# ============================================================
# VERIFY CONNECTION CODE
# ============================================================

class VerifyConnectionCodeRequest(BaseModel):
    requester_user_id: str
    target_user_id: str
    code: str


# ============================================================
# NOTIFICATION READ
# ============================================================

class NotificationReadRequest(BaseModel):
    notification_id: int
    user_id: str


# ============================================================
# DATABASE
# ============================================================

from database import (
    SessionLocal,
    User,
    OTPVerification,
    ConnectionRequest,
    ConnectionCode,
    Notification,
    Connection
)


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
# OTP
# ============================================================

def generate_otp():

    return str(
        secrets.randbelow(900000) + 100000
    )


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
        expires_at=(
            datetime.utcnow()
            + timedelta(minutes=2)
        ),
        verified=False
    )

    db.add(new_otp)

    db.commit()

    return otp


# ============================================================
# SEARCH PAGE
# ============================================================

@app.get("/search")
async def search_page():

    search_file = os.path.join(
        BASE_DIR,
        "search.html"
    )

    if not os.path.isfile(search_file):

        raise HTTPException(
            status_code=404,
            detail="search.html file not found on server"
        )

    return FileResponse(search_file)


@app.get("/search.html")
async def search_html():

    search_file = os.path.join(
        BASE_DIR,
        "search.html"
    )

    if not os.path.isfile(search_file):

        raise HTTPException(
            status_code=404,
            detail="search.html file not found on server"
        )

    return FileResponse(search_file)


# ============================================================
# SEARCH API
#
# Search by:
# User ID
# OR
# Mobile number
#
# Mobile number is NEVER returned publicly.
# ============================================================

@app.get("/api/search")
async def search_users(
    q: str = "",
    db: Session = Depends(get_db)
):

    q = q.strip()

    if not q:

        return {
            "ok": True,
            "users": []
        }

    users = (
        db.query(User)
        .filter(
            (User.user_id.ilike(f"%{q}%"))
            |
            (User.mobile.ilike(f"%{q}%"))
        )
        .limit(20)
        .all()
    )

    return {
        "ok": True,

        "users": [

            {
                "user_id": user.user_id,
                "name": user.name,
                "profile_photo": user.profile_photo
            }

            for user in users
        ]
    }


# ============================================================
# REGISTER PAGE
# ============================================================

@app.get("/")
async def register_page():

    register_file = os.path.join(
        BASE_DIR,
        "register.html"
    )

    if not os.path.isfile(register_file):

        raise HTTPException(
            status_code=404,
            detail="register.html file not found"
        )

    return FileResponse(register_file)


@app.get("/register.html")
async def register_html():

    register_file = os.path.join(
        BASE_DIR,
        "register.html"
    )

    if not os.path.isfile(register_file):

        raise HTTPException(
            status_code=404,
            detail="register.html file not found"
        )

    return FileResponse(register_file)


# ============================================================
# LOGIN
# USER ID OR MOBILE
# ============================================================

@app.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    identifier = request.identifier.strip()

    password = request.password

    if not identifier or not password:

        return {
            "ok": False,
            "message":
                "User ID/mobile and password are required"
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier)
            |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:

        return {
            "ok": False,
            "message":
                "Invalid User ID/mobile or password"
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
            "message":
                "Invalid User ID/mobile or password"
        }

    token = secrets.token_urlsafe(32)

    # IMPORTANT:
    # User data is returned BOTH directly
    # AND inside "user".
    #
    # This makes old and new frontend code compatible.

    return {

        "ok": True,

        "message":
            "Login successful",

        "token":
            token,

        # ----------------------------------------------------
        # DIRECT USER DATA
        # ----------------------------------------------------

        "user_id":
            user.user_id,

        "name":
            user.name,

        "mobile":
            user.mobile,

        "profile_photo":
            user.profile_photo,

        # ----------------------------------------------------
        # NESTED USER DATA
        # ----------------------------------------------------

        "user": {

            "user_id":
                user.user_id,

            "name":
                user.name,

            "mobile":
                user.mobile,

            "profile_photo":
                user.profile_photo
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

    if not name:

        return {
            "ok": False,
            "message": "Name is required"
        }

    if not mobile:

        return {
            "ok": False,
            "message":
                "Mobile number is required"
        }

    if (
        not mobile.isdigit()
        or len(mobile) != 10
    ):

        return {
            "ok": False,
            "message":
                "Enter a valid 10-digit mobile number"
        }

    if not password:

        return {
            "ok": False,
            "message":
                "Password is required"
        }

    if len(password) < 6:

        return {
            "ok": False,
            "message":
                "Password must be at least 6 characters"
        }

    existing_user = (
        db.query(User)
        .filter(
            User.mobile == mobile
        )
        .first()
    )

    if existing_user:

        return {
            "ok": False,
            "message":
                "Mobile number already registered"
        }

    otp = save_otp(
        db,
        mobile,
        "register"
    )

    return {

        "ok": True,

        "message":
            "OTP generated",

        "otp":
            otp,

        "expires_in":
            120
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
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message":
                "OTP not found. Please request a new OTP"
        }

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)

        db.commit()

        return {
            "ok": False,
            "message":
                "OTP expired. Please request a new OTP"
        }

    if verification.otp != otp:

        return {
            "ok": False,
            "message":
                "Invalid OTP"
        }

    existing_user = (
        db.query(User)
        .filter(
            User.mobile == mobile
        )
        .first()
    )

    if existing_user:

        return {
            "ok": False,
            "message":
                "Mobile number already registered"
        }

    user_id = (
        "UX"
        + uuid.uuid4().hex[:10]
    )

    password_hash = (
        password_hasher.hash(
            request.password
        )
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
            "message":
                "Registration failed. Please try again"
        }

    return {

        "ok": True,

        "message":
            "Registration successful",

        "user_id":
            new_user.user_id,

        "name":
            new_user.name,

        "mobile":
            new_user.mobile,

        "profile_photo":
            new_user.profile_photo
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
            "message":
                "User ID or mobile number is required"
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier)
            |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:

        return {
            "ok": False,
            "message":
                "User ID or mobile number not found"
        }

    otp = save_otp(
        db,
        user.mobile,
        "forgot_password"
    )

    return {

        "ok": True,

        "message":
            "OTP generated",

        "otp":
            otp,

        "expires_in":
            120
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
            (User.user_id == identifier)
            |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:

        return {
            "ok": False,
            "message":
                "User not found"
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier
            == user.mobile,

            OTPVerification.purpose
            == "forgot_password",

            OTPVerification.verified
            == False
        )
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message":
                "OTP not found. Please request a new OTP"
        }

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)

        db.commit()

        return {
            "ok": False,
            "message":
                "OTP expired. Please request a new OTP"
        }

    if verification.otp != otp:

        return {
            "ok": False,
            "message":
                "Invalid OTP"
        }

    verification.verified = True

    db.commit()

    return {

        "ok": True,

        "message":
            "OTP verified"
    }


# ============================================================
# RESET PASSWORD
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
            "message":
                "Password must be at least 6 characters"
        }

    if (
        request.new_password
        !=
        request.confirm_password
    ):

        return {
            "ok": False,
            "message":
                "Passwords do not match"
        }

    user = (
        db.query(User)
        .filter(
            (User.user_id == identifier)
            |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:

        return {
            "ok": False,
            "message":
                "User not found"
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier
            == user.mobile,

            OTPVerification.purpose
            == "forgot_password",

            OTPVerification.verified
            == True
        )
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message":
                "OTP verification required"
        }

    if datetime.utcnow() > verification.expires_at:

        verification.verified = False

        db.commit()

        return {
            "ok": False,
            "message":
                "OTP verification expired"
        }

    user.password_hash = (
        password_hasher.hash(
            request.new_password
        )
    )

    verification.verified = False

    db.commit()

    return {
        "ok": True,
        "message":
            "Password changed successfully"
    }


# ============================================================
# FOLLOW SYSTEM
# ============================================================


# ============================================================
# SEND FOLLOW REQUEST
# ============================================================

@app.post("/api/follow")
async def follow_user(
    request: FollowRequest,
    db: Session = Depends(get_db)
):

    requester_id = (
        request.requester_user_id.strip()
    )

    target_id = (
        request.target_user_id.strip()
    )

    if not requester_id or not target_id:

        return {
            "ok": False,
            "message":
                "User IDs are required"
        }

    if requester_id == target_id:

        return {
            "ok": False,
            "message":
                "You cannot follow your own account"
        }

    requester = (
        db.query(User)
        .filter(
            User.user_id == requester_id
        )
        .first()
    )

    target = (
        db.query(User)
        .filter(
            User.user_id == target_id
        )
        .first()
    )

    if not requester:

        return {
            "ok": False,
            "message":
                "Requester account not found"
        }

    if not target:

        return {
            "ok": False,
            "message":
                "User not found"
        }

    # --------------------------------------------------------
    # Already connected
    # --------------------------------------------------------

    existing_connection = (
        db.query(Connection)
        .filter(
            (
                (Connection.user_a_id == requester_id)
                &
                (Connection.user_b_id == target_id)
            )
            |
            (
                (Connection.user_a_id == target_id)
                &
                (Connection.user_b_id == requester_id)
            )
        )
        .first()
    )

    if existing_connection:

        return {
            "ok": True,
            "status": "verified",
            "message":
                "You are already connected"
        }

    # --------------------------------------------------------
    # Existing request
    # --------------------------------------------------------

    existing_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.requester_user_id
            == requester_id,

            ConnectionRequest.target_user_id
            == target_id
        )
        .order_by(
            ConnectionRequest.id.desc()
        )
        .first()
    )

    if existing_request:

        if existing_request.status == "pending":

            return {
                "ok": True,
                "status": "pending",
                "message":
                    "Follow request already sent"
            }

        if existing_request.status == "accepted":

            return {
                "ok": True,
                "status": "accepted",
                "message":
                    "Request accepted. Verification code required"
            }

        if existing_request.status == "verified":

            return {
                "ok": True,
                "status": "verified",
                "message":
                    "Connection already verified"
            }

        # rejected -> allow again

        existing_request.status = "pending"

        existing_request.updated_at = datetime.utcnow()

        request_row = existing_request

    else:

        request_row = ConnectionRequest(
            requester_user_id=requester_id,
            target_user_id=target_id,
            status="pending"
        )

        db.add(request_row)

        db.flush()

    # --------------------------------------------------------
    # Notification
    # --------------------------------------------------------

    notification = Notification(
        receiver_user_id=target_id,
        sender_user_id=requester_id,
        type="follow_request",
        title="New Follow Request",
        message=(
            f"{requester.name} wants to connect with you."
        ),
        connection_request_id=request_row.id,
        verification_code=None,
        is_read=False
    )

    db.add(notification)

    db.commit()

    return {
        "ok": True,
        "status": "pending",
        "message":
            "Follow request sent"
    }


# ============================================================
# FOLLOW STATUS
# ============================================================

@app.get("/api/follow/status")
async def follow_status(
    requester_user_id: str,
    target_user_id: str,
    db: Session = Depends(get_db)
):

    requester_id = requester_user_id.strip()

    target_id = target_user_id.strip()

    if not requester_id or not target_id:

        return {
            "ok": False,
            "message":
                "User IDs are required"
        }

    connection = (
        db.query(Connection)
        .filter(
            (
                (Connection.user_a_id == requester_id)
                &
                (Connection.user_b_id == target_id)
            )
            |
            (
                (Connection.user_a_id == target_id)
                &
                (Connection.user_b_id == requester_id)
            )
        )
        .first()
    )

    if connection:

        return {
            "ok": True,
            "status": "verified"
        }

    row = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.requester_user_id
            == requester_id,

            ConnectionRequest.target_user_id
            == target_id
        )
        .order_by(
            ConnectionRequest.id.desc()
        )
        .first()
    )

    if not row:

        return {
            "ok": True,
            "status": "none"
        }

    return {
        "ok": True,
        "status": row.status
    }


# ============================================================
# GET NOTIFICATIONS
# ============================================================

@app.get("/api/notifications")
async def get_notifications(
    user_id: str,
    db: Session = Depends(get_db)
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": False,
            "message":
                "User ID is required"
        }

    notifications = (
        db.query(Notification)
        .filter(
            Notification.receiver_user_id
            == user_id
        )
        .order_by(
            Notification.id.desc()
        )
        .limit(50)
        .all()
    )

    result = []

    for notification in notifications:

        sender = None

        if notification.sender_user_id:

            sender = (
                db.query(User)
                .filter(
                    User.user_id
                    == notification.sender_user_id
                )
                .first()
            )

        result.append({

            "id":
                notification.id,

            "type":
                notification.type,

            "title":
                notification.title,

            "message":
                notification.message,

            "sender": {

                "user_id":
                    sender.user_id
                    if sender else None,

                "name":
                    sender.name
                    if sender else None,

                "profile_photo":
                    sender.profile_photo
                    if sender else None
            },

            "connection_request_id":
                notification.connection_request_id,

            "verification_code":
                notification.verification_code,

            "is_read":
                notification.is_read,

            "created_at":
                notification.created_at.isoformat()
        })

    return {
        "ok": True,
        "notifications": result
    }


# ============================================================
# ACCEPT FOLLOW REQUEST
# ============================================================

@app.post("/api/follow/accept")
async def accept_follow(
    request: ConnectionActionRequest,
    db: Session = Depends(get_db)
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id
            == request.notification_id,

            Notification.receiver_user_id
            == request.user_id
        )
        .first()
    )

    if not notification:

        return {
            "ok": False,
            "message":
                "Notification not found"
        }

    if notification.type != "follow_request":

        return {
            "ok": False,
            "message":
                "Invalid follow request"
        }

    connection_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.id
            == notification.connection_request_id,

            ConnectionRequest.target_user_id
            == request.user_id
        )
        .first()
    )

    if not connection_request:

        return {
            "ok": False,
            "message":
                "Follow request not found"
        }

    if connection_request.status == "verified":

        return {
            "ok": True,
            "status": "verified",
            "message":
                "Connection already verified"
        }

    requester_id = (
        connection_request.requester_user_id
    )

    target_id = (
        connection_request.target_user_id
    )

    requester = (
        db.query(User)
        .filter(
            User.user_id == requester_id
        )
        .first()
    )

    target = (
        db.query(User)
        .filter(
            User.user_id == target_id
        )
        .first()
    )

    if not requester or not target:

        return {
            "ok": False,
            "message":
                "User account not found"
        }

    # --------------------------------------------------------
    # Mark accepted
    # --------------------------------------------------------

    connection_request.status = "accepted"

    connection_request.updated_at = datetime.utcnow()

    notification.is_read = True

    # --------------------------------------------------------
    # Invalidate old codes
    # --------------------------------------------------------

    old_codes = (
        db.query(ConnectionCode)
        .filter(
            ConnectionCode.requester_user_id
            == requester_id,

            ConnectionCode.target_user_id
            == target_id,

            ConnectionCode.verified
            == False
        )
        .all()
    )

    for old_code in old_codes:

        old_code.verified = True

    # --------------------------------------------------------
    # Generate new verification code
    # --------------------------------------------------------

    code = generate_otp()

    connection_code = ConnectionCode(

        requester_user_id=requester_id,

        target_user_id=target_id,

        code=code,

        expires_at=(
            datetime.utcnow()
            + timedelta(minutes=10)
        ),

        verified=False
    )

    db.add(connection_code)

    # --------------------------------------------------------
    # Notification to requester
    # --------------------------------------------------------

    requester_notification = Notification(

        receiver_user_id=requester_id,

        sender_user_id=target_id,

        type="connection_code",

        title="Connection Accepted",

        message=(
            f"{target.name} accepted your connection request. "
            f"Your verification code is {code}. "
            f"Search {target.user_id} and enter this code."
        ),

        connection_request_id=
            connection_request.id,

        verification_code=code,

        is_read=False
    )

    db.add(requester_notification)

    db.commit()

    return {

        "ok": True,

        "status": "accepted",

        "message":
            "Request accepted. Verification code sent",

        "verification_code":
            code
    }


# ============================================================
# REJECT FOLLOW REQUEST
# ============================================================

@app.post("/api/follow/reject")
async def reject_follow(
    request: ConnectionActionRequest,
    db: Session = Depends(get_db)
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id
            == request.notification_id,

            Notification.receiver_user_id
            == request.user_id
        )
        .first()
    )

    if not notification:

        return {
            "ok": False,
            "message":
                "Notification not found"
        }

    if notification.type != "follow_request":

        return {
            "ok": False,
            "message":
                "Invalid follow request"
        }

    connection_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.id
            == notification.connection_request_id,

            ConnectionRequest.target_user_id
            == request.user_id
        )
        .first()
    )

    if not connection_request:

        return {
            "ok": False,
            "message":
                "Follow request not found"
        }

    requester_id = (
        connection_request.requester_user_id
    )

    target_id = (
        connection_request.target_user_id
    )

    target = (
        db.query(User)
        .filter(
            User.user_id == target_id
        )
        .first()
    )

    connection_request.status = "rejected"

    connection_request.updated_at = datetime.utcnow()

    notification.is_read = True

    requester_notification = Notification(

        receiver_user_id=requester_id,

        sender_user_id=target_id,

        type="follow_rejected",

        title="Connection Request Rejected",

        message=(
            f"{target.name if target else target_id} "
            "rejected your connection request."
        ),

        connection_request_id=
            connection_request.id,

        verification_code=None,

        is_read=False
    )

    db.add(requester_notification)

    db.commit()

    return {

        "ok": True,

        "status": "rejected",

        "message":
            "Follow request rejected"
    }


# ============================================================
# VERIFY CONNECTION CODE
# ============================================================

@app.post("/api/follow/verify")
async def verify_connection(
    request: VerifyConnectionCodeRequest,
    db: Session = Depends(get_db)
):

    requester_id = (
        request.requester_user_id.strip()
    )

    target_id = (
        request.target_user_id.strip()
    )

    code = request.code.strip()

    if not requester_id or not target_id:

        return {
            "ok": False,
            "message":
                "User IDs are required"
        }

    if not code:

        return {
            "ok": False,
            "message":
                "Verification code is required"
        }

    # --------------------------------------------------------
    # Find request
    # --------------------------------------------------------

    connection_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.requester_user_id
            == requester_id,

            ConnectionRequest.target_user_id
            == target_id
        )
        .order_by(
            ConnectionRequest.id.desc()
        )
        .first()
    )

    if not connection_request:

        return {
            "ok": False,
            "message":
                "Connection request not found"
        }

    if connection_request.status != "accepted":

        if connection_request.status == "verified":

            return {
                "ok": True,
                "status": "verified",
                "message":
                    "Connection already verified"
            }

        return {
            "ok": False,
            "message":
                "Connection has not been accepted"
        }

    # --------------------------------------------------------
    # Find active code
    # --------------------------------------------------------

    connection_code = (
        db.query(ConnectionCode)
        .filter(
            ConnectionCode.requester_user_id
            == requester_id,

            ConnectionCode.target_user_id
            == target_id,

            ConnectionCode.verified
            == False
        )
        .order_by(
            ConnectionCode.id.desc()
        )
        .first()
    )

    if not connection_code:

        return {
            "ok": False,
            "message":
                "Verification code not found"
        }

    # --------------------------------------------------------
    # Expiry
    # --------------------------------------------------------

    if datetime.utcnow() > connection_code.expires_at:

        connection_code.verified = True

        db.commit()

        return {
            "ok": False,
            "message":
                "Verification code expired"
        }

    # --------------------------------------------------------
    # Check code
    # --------------------------------------------------------

    if connection_code.code != code:

        return {
            "ok": False,
            "message":
                "Invalid verification code"
        }

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    connection_code.verified = True

    connection_request.status = "verified"

    connection_request.updated_at = datetime.utcnow()

    # --------------------------------------------------------
    # Avoid duplicate connection
    # --------------------------------------------------------

    existing_connection = (
        db.query(Connection)
        .filter(
            (
                (Connection.user_a_id == requester_id)
                &
                (Connection.user_b_id == target_id)
            )
            |
            (
                (Connection.user_a_id == target_id)
                &
                (Connection.user_b_id == requester_id)
            )
        )
        .first()
    )

    if not existing_connection:

        new_connection = Connection(

            user_a_id=requester_id,

            user_b_id=target_id
        )

        db.add(new_connection)

    # --------------------------------------------------------
    # Get users
    # --------------------------------------------------------

    target = (
        db.query(User)
        .filter(
            User.user_id == target_id
        )
        .first()
    )

    requester = (
        db.query(User)
        .filter(
            User.user_id == requester_id
        )
        .first()
    )

    # --------------------------------------------------------
    # Notifications
    # --------------------------------------------------------

    db.add(
        Notification(

            receiver_user_id=target_id,

            sender_user_id=requester_id,

            type="connection_verified",

            title="Connection Verified",

            message=(
                f"You are now connected with "
                f"{requester.name if requester else requester_id}."
            ),

            connection_request_id=
                connection_request.id,

            verification_code=None,

            is_read=False
        )
    )

    db.add(
        Notification(

            receiver_user_id=requester_id,

            sender_user_id=target_id,

            type="connection_verified",

            title="Connection Verified",

            message=(
                f"You are now connected with "
                f"{target.name if target else target_id}."
            ),

            connection_request_id=
                connection_request.id,

            verification_code=None,

            is_read=False
        )
    )

    db.commit()

    return {

        "ok": True,

        "status": "verified",

        "message":
            "Connection verified successfully"
    }


# ============================================================
# MARK NOTIFICATION READ
# ============================================================

@app.post("/api/notifications/read")
async def mark_notification_read(
    request: NotificationReadRequest,
    db: Session = Depends(get_db)
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id
            == request.notification_id,

            Notification.receiver_user_id
            == request.user_id
        )
        .first()
    )

    if not notification:

        return {
            "ok": False,
            "message":
                "Notification not found"
        }

    notification.is_read = True

    db.commit()

    return {
        "ok": True,
        "message":
            "Notification marked as read"
    }


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/home")
async def home_page():

    home_file = os.path.join(
        BASE_DIR,
        "home.html"
    )

    if not os.path.isfile(home_file):

        raise HTTPException(
            status_code=404,
            detail="home.html file not found"
        )

    return FileResponse(home_file)


# ============================================================
# HOME CONNECTIONS
#
# ONLY VERIFIED CONNECTIONS EXIST IN connections TABLE.
# Therefore Home will only show verified connections.
# ============================================================

@app.get("/api/home/connections")
async def home_connections(
    user_id: str = "",
    db: Session = Depends(get_db)
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": True,
            "users": []
        }

    connections = (
        db.query(Connection)
        .filter(
            (Connection.user_a_id == user_id)
            |
            (Connection.user_b_id == user_id)
        )
        .order_by(
            Connection.id.desc()
        )
        .all()
    )

    users = []

    seen = set()

    for connection in connections:

        if connection.user_a_id == user_id:

            other_id = connection.user_b_id

        else:

            other_id = connection.user_a_id

        if other_id in seen:
            continue

        seen.add(other_id)

        user = (
            db.query(User)
            .filter(
                User.user_id == other_id
            )
            .first()
        )

        if not user:
            continue

        users.append({

            "user_id":
                user.user_id,

            "name":
                user.name,

            "profile_photo":
                user.profile_photo
        })

    return {

        "ok": True,

        "users":
            users
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    return {

        "ok": True,

        "status":
            "online",

        "app":
            "Usanex"
    }


# ============================================================
# LOCAL RUN
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
