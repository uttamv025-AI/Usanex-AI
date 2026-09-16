from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
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
import asyncio


# ============================================================
# APP
# ============================================================

app = FastAPI(title="Usanex")

password_hasher = PasswordHasher()

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# REAL-TIME WEBSOCKET MANAGER
# ============================================================

class ConnectionManager:

    def __init__(self):

        self.active_connections = {}

        self.lock = asyncio.Lock()

    async def connect(
        self,
        user_id: str,
        websocket: WebSocket
    ):

        await websocket.accept()

        async with self.lock:

            if user_id not in self.active_connections:

                self.active_connections[user_id] = set()

            self.active_connections[user_id].add(
                websocket
            )

    async def disconnect(
        self,
        user_id: str,
        websocket: WebSocket
    ):

        async with self.lock:

            if user_id not in self.active_connections:
                return

            self.active_connections[user_id].discard(
                websocket
            )

            if not self.active_connections[user_id]:

                del self.active_connections[user_id]

    async def send_to_user(
        self,
        user_id: str,
        data: dict
    ):

        async with self.lock:

            sockets = list(
                self.active_connections.get(
                    user_id,
                    set()
                )
            )

        dead_connections = []

        for websocket in sockets:

            try:

                await websocket.send_json(data)

            except Exception:

                dead_connections.append(
                    websocket
                )

        for websocket in dead_connections:

            await self.disconnect(
                user_id,
                websocket
            )


manager = ConnectionManager()


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


class FollowRequest(BaseModel):

    requester_user_id: str
    target_user_id: str


class ConnectionActionRequest(BaseModel):

    notification_id: int
    user_id: str


class VerifyConnectionCodeRequest(BaseModel):

    requester_user_id: str
    target_user_id: str
    code: str


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
# WEBSOCKET
# ============================================================

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str
):

    user_id = user_id.strip()

    if not user_id:

        await websocket.close()

        return

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(
                User.user_id == user_id
            )
            .first()
        )

        if not user:

            await websocket.close(
                code=1008
            )

            return

    finally:

        db.close()

    await manager.connect(
        user_id,
        websocket
    )

    try:

        await websocket.send_json({

            "type":
                "websocket_connected",

            "message":
                "Real-time connection active",

            "user_id":
                user_id
        })

        while True:

            try:

                data = await websocket.receive_text()

                if data == "ping":

                    await websocket.send_json({

                        "type":
                            "pong",

                        "timestamp":
                            datetime.utcnow().isoformat()
                    })

            except WebSocketDisconnect:

                break

            except Exception:

                break

    finally:

        await manager.disconnect(
            user_id,
            websocket
        )


# ============================================================
# HELPER:
# SEND REAL-TIME NOTIFICATION
# ============================================================

async def push_notification(
    user_id: str,
    notification_type: str,
    notification_id: int,
    title: str,
    message: str,
    sender: dict | None = None,
    connection_request_id: int | None = None,
    verification_code: str | None = None
):

    await manager.send_to_user(

        user_id,

        {

            "type":
                "notification",

            "notification": {

                "id":
                    notification_id,

                "notification_type":
                    notification_type,

                "title":
                    title,

                "message":
                    message,

                "sender":
                    sender,

                "connection_request_id":
                    connection_request_id,

                "verification_code":
                    verification_code,

                "is_read":
                    False,

                "created_at":
                    datetime.utcnow().isoformat()
            }
        }
    )


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

                "user_id":
                    user.user_id,

                "name":
                    user.name,

                "profile_photo":
                    user.profile_photo

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

    return {

        "ok": True,

        "message":
            "Login successful",

        "token":
            token,

        "user_id":
            user.user_id,

        "name":
            user.name,

        "mobile":
            user.mobile,

        "profile_photo":
            user.profile_photo,

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
        != request.confirm_password
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

    requester_id = request.requester_user_id.strip()

    target_id = request.target_user_id.strip()

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

    db.refresh(notification)

    await push_notification(

        target_id,

        "follow_request",

        notification.id,

        notification.title,

        notification.message,

        sender={

            "user_id":
                requester.user_id,

            "name":
                requester.name,

            "profile_photo":
                requester.profile_photo
        },

        connection_request_id=
            request_row.id
    )

    return {

        "ok": True,

        "status": "pending",

        "message":
            "Follow request sent",

        "notification_id":
            notification.id
    }


# ============================================================
# CANCEL FOLLOW REQUEST
# ============================================================

@app.post("/api/follow/cancel")
async def cancel_follow(
    request: FollowRequest,
    db: Session = Depends(get_db)
):

    requester_id = request.requester_user_id.strip()

    target_id = request.target_user_id.strip()

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
                "Invalid request"
        }

    connection_request = (

        db.query(ConnectionRequest)

        .filter(

            ConnectionRequest.requester_user_id
            == requester_id,

            ConnectionRequest.target_user_id
            == target_id,

            ConnectionRequest.status
            == "pending"

        )

        .order_by(
            ConnectionRequest.id.desc()
        )

        .first()
    )

    if not connection_request:

        return {

            "ok": True,

            "status": "none",

            "message":
                "No pending request"
        }

    request_id = connection_request.id

    connection_request.status = "rejected"

    connection_request.updated_at = datetime.utcnow()

    pending_notifications = (

        db.query(Notification)

        .filter(

            Notification.receiver_user_id
            == target_id,

            Notification.sender_user_id
            == requester_id,

            Notification.connection_request_id
            == request_id,

            Notification.type
            == "follow_request",

            Notification.is_read
            == False

        )

        .all()
    )

    for notification in pending_notifications:

        notification.is_read = True

    db.commit()

    await manager.send_to_user(

        target_id,

        {

            "type":
                "follow_cancelled",

            "requester_user_id":
                requester_id,

            "target_user_id":
                target_id,

            "connection_request_id":
                request_id
        }
    )

    return {

        "ok": True,

        "status": "none",

        "message":
            "Follow request cancelled"
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

    if row.status == "rejected":

        return {

            "ok": True,

            "status": "none"
        }

    return {

        "ok": True,

        "status": row.status
    }


# ============================================================
# NOTIFICATIONS PAGE
# ============================================================

@app.get("/notifications")
async def notifications_page():

    notifications_file = os.path.join(
        BASE_DIR,
        "notifications.html"
    )

    if not os.path.isfile(notifications_file):

        raise HTTPException(
            status_code=404,
            detail="notifications.html file not found"
        )

    return FileResponse(notifications_file)


@app.get("/notifications.html")
async def notifications_html():

    notifications_file = os.path.join(
        BASE_DIR,
        "notifications.html"
    )

    if not os.path.isfile(notifications_file):

        raise HTTPException(
            status_code=404,
            detail="notifications.html file not found"
        )

    return FileResponse(notifications_file)


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

        "notifications":
            result
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

    connection_request.status = "accepted"

    connection_request.updated_at = datetime.utcnow()

    notification.is_read = True

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

    db.refresh(requester_notification)

    await push_notification(

        requester_id,

        "connection_code",

        requester_notification.id,

        requester_notification.title,

        requester_notification.message,

        sender={

            "user_id":
                target.user_id,

            "name":
                target.name,

            "profile_photo":
                target.profile_photo

        },

        connection_request_id=
            connection_request.id,

        verification_code=code
    )

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

    db.refresh(requester_notification)

    await push_notification(

        requester_id,

        "follow_rejected",

        requester_notification.id,

        requester_notification.title,

        requester_notification.message,

        sender={

            "user_id":
                target.user_id
                if target else target_id,

            "name":
                target.name
                if target else target_id,

            "profile_photo":
                target.profile_photo
                if target else None

        },

        connection_request_id=
            connection_request.id
    )

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

    requester_id = request.requester_user_id.strip()

    target_id = request.target_user_id.strip()

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

    if datetime.utcnow() > connection_code.expires_at:

        connection_code.verified = True

        db.commit()

        return {

            "ok": False,

            "message":
                "Verification code expired"
        }

    if connection_code.code != code:

        return {

            "ok": False,

            "message":
                "Invalid verification code"
        }

    connection_code.verified = True

    connection_request.status = "verified"

    connection_request.updated_at = datetime.utcnow()

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

    target_notification = Notification(

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

    requester_notification = Notification(

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

    db.add(target_notification)

    db.add(requester_notification)

    db.commit()

    db.refresh(target_notification)

    db.refresh(requester_notification)

    await push_notification(

        target_id,

        "connection_verified",

        target_notification.id,

        target_notification.title,

        target_notification.message,

        sender={

            "user_id":
                requester.user_id
                if requester else requester_id,

            "name":
                requester.name
                if requester else requester_id,

            "profile_photo":
                requester.profile_photo
                if requester else None

        },

        connection_request_id=
            connection_request.id
    )

    await push_notification(

        requester_id,

        "connection_verified",

        requester_notification.id,

        requester_notification.title,

        requester_notification.message,

        sender={

            "user_id":
                target.user_id
                if target else target_id,

            "name":
                target.name
                if target else target_id,

            "profile_photo":
                target.profile_photo
                if target else None

        },

        connection_request_id=
            connection_request.id
    )

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
            "Usanex",

        "realtime":
            "websocket"
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
