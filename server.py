from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    
)

from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
)

from datetime import datetime, timedelta

import secrets
import uuid
import os
import asyncio

import cloudinary
import cloudinary.uploader


# ============================================================
# APP
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

app = FastAPI(title="Usanex")

# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=os.path.join(
            BASE_DIR,
            "static"
        )
    ),
    name="static",
)


# ============================================================
# CLOUDINARY
# ============================================================

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


password_hasher = PasswordHasher()


# ============================================================
# DATABASE
# ============================================================

from database import (
    SessionLocal,
    User,
    UserPresence,
    OTPVerification,
    ConnectionRequest,
    ConnectionCode,
    Notification,
    Connection,
    ChatMessage,
    Status,
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
# REAL-TIME WEBSOCKET MANAGER
# ============================================================

class ConnectionManager:

    def __init__(self):
        self.active_connections = {}
        self.lock = asyncio.Lock()

    async def connect(
        self,
        user_id: str,
        websocket: WebSocket,
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
        websocket: WebSocket,
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
        data: dict,
    ):
        async with self.lock:

            sockets = list(
                self.active_connections.get(
                    user_id,
                    set(),
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
                websocket,
            )

    async def is_online(
        self,
        user_id: str,
    ):
        async with self.lock:

            return bool(
                self.active_connections.get(
                    user_id,
                    set(),
                )
            )


manager = ConnectionManager()


# ============================================================
# USER PRESENCE
# ============================================================

def set_user_presence(
    user_id: str,
    is_online: bool,
):
    db = SessionLocal()

    try:

        now = datetime.utcnow()

        presence = (
            db.query(UserPresence)
            .filter(
                UserPresence.user_id == user_id
            )
            .first()
        )

        if not presence:

            presence = UserPresence(
                user_id=user_id,
                is_online=is_online,
                last_seen_at=(
                    None
                    if is_online
                    else now
                ),
                updated_at=now,
            )

            db.add(presence)

        else:

            presence.is_online = is_online
            presence.updated_at = now

            if not is_online:
                presence.last_seen_at = now

        db.commit()

        return presence.last_seen_at

    finally:
        db.close()


async def broadcast_presence(
    user_id: str,
    is_online: bool,
    last_seen_at=None,
):
    db = SessionLocal()

    try:

        connections = (
            db.query(Connection)
            .filter(
                (Connection.user_a_id == user_id)
                |
                (Connection.user_b_id == user_id)
            )
            .all()
        )

        other_user_ids = []

        for connection in connections:

            if connection.user_a_id == user_id:
                other_id = connection.user_b_id
            else:
                other_id = connection.user_a_id

            if other_id not in other_user_ids:
                other_user_ids.append(
                    other_id
                )

    finally:
        db.close()

    payload = {
        "type": "user_presence",
        "user_id": user_id,
        "is_online": is_online,
        "last_seen_at": (
            None
            if is_online
            else (
                last_seen_at.isoformat()
                if last_seen_at
                else None
            )
        ),
    }

    for other_user_id in other_user_ids:

        await manager.send_to_user(
            other_user_id,
            payload,
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


class SendMessageRequest(BaseModel):
    sender_user_id: str
    receiver_user_id: str
    message: str


# ============================================================
# OTP FUNCTIONS
# ============================================================

def generate_otp():
    return str(
        secrets.randbelow(900000) + 100000
    )


def save_otp(
    db: Session,
    identifier: str,
    purpose: str,
):
    otp = generate_otp()

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

    new_otp = OTPVerification(
        identifier=identifier,
        otp=otp,
        purpose=purpose,
        expires_at=(
            datetime.utcnow()
            + timedelta(minutes=2)
        ),
        verified=False,
    )

    db.add(new_otp)
    db.commit()

    return otp


# ============================================================
# REAL-TIME NOTIFICATION HELPER
# ============================================================

async def push_notification(
    user_id: str,
    notification_type: str,
    notification_id: int,
    title: str,
    message: str,
    sender: dict | None = None,
    connection_request_id: int | None = None,
    verification_code: str | None = None,
    requester_user_id: str | None = None,
    target_user_id: str | None = None,
):

    await manager.send_to_user(
        user_id,
        {
            "type": "notification",
            "notification": {
                "id": notification_id,
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "sender": sender,
                "connection_request_id": connection_request_id,
                "verification_code": verification_code,
                "requester_user_id": requester_user_id,
                "target_user_id": target_user_id,
                "is_read": False,
                "created_at": datetime.utcnow().isoformat(),
            },
        },
    )


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
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
        websocket,
    )

    set_user_presence(
        user_id,
        True,
    )

    await broadcast_presence(
        user_id,
        True,
    )

    try:

        await websocket.send_json(
            {
                "type": "websocket_connected",
                "message": "Real-time connection active",
                "user_id": user_id,
                "is_online": True,
            }
        )

        while True:

            try:

                data = await websocket.receive_text()

                if data == "ping":

                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            except WebSocketDisconnect:
                break

            except Exception:
                break

    finally:

        await manager.disconnect(
            user_id,
            websocket,
        )

        still_online = await manager.is_online(
            user_id
        )

        if not still_online:

            last_seen = set_user_presence(
                user_id,
                False,
            )

            await broadcast_presence(
                user_id,
                False,
                last_seen,
            )


# ============================================================
# CHAT PRESENCE API
# ============================================================

@app.get("/api/chat/presence")
async def chat_presence(
    user_id: str,
    other_user_id: str,
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()
    other_user_id = other_user_id.strip()

    if not user_id or not other_user_id:

        raise HTTPException(
            status_code=400,
            detail="User IDs are required",
        )

    if user_id == other_user_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid users",
        )

    if not are_connected(
        db,
        user_id,
        other_user_id,
    ):

        raise HTTPException(
            status_code=403,
            detail="Not connected",
        )

    online = await manager.is_online(
        other_user_id
    )

    presence = (
        db.query(UserPresence)
        .filter(
            UserPresence.user_id
            == other_user_id
        )
        .first()
    )

    last_seen_at = None

    if (
        presence
        and presence.last_seen_at
    ):
        last_seen_at = (
            presence.last_seen_at.isoformat()
        )

    return {
        "ok": True,
        "user_id": other_user_id,
        "is_online": online,
        "status": (
            "online"
            if online
            else "offline"
        ),
        "last_seen_at": (
            None
            if online
            else last_seen_at
        ),
    }


# ============================================================
# SEARCH PAGE
# ============================================================

@app.get("/search")
async def search_page():

    search_file = os.path.join(
        BASE_DIR,
        "search.html",
    )

    if not os.path.isfile(search_file):

        raise HTTPException(
            status_code=404,
            detail="search.html file not found on server",
        )

    return FileResponse(search_file)


@app.get("/search.html")
async def search_html():

    search_file = os.path.join(
        BASE_DIR,
        "search.html",
    )

    if not os.path.isfile(search_file):

        raise HTTPException(
            status_code=404,
            detail="search.html file not found on server",
        )

    return FileResponse(search_file)


# ============================================================
# SEARCH API
# ============================================================

@app.get("/api/search")
async def search_users(
    q: str = "",
    db: Session = Depends(get_db),
):

    q = q.strip()

    if not q:

        return {
            "ok": True,
            "users": [],
        }

    users = (
        db.query(User)
        .filter(
            (User.user_id.ilike(f"%{q}%"))
            |
            (User.mobile.ilike(f"%{q}%"))
            |
            (User.name.ilike(f"%{q}%"))
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
                "profile_photo": user.profile_photo,
                "profile_picture": user.profile_photo,
            }
            for user in users
        ],
    }


# ============================================================
# REGISTER PAGE
# ============================================================

@app.get("/")
async def register_page():

    register_file = os.path.join(
        BASE_DIR,
        "register.html",
    )

    if not os.path.isfile(register_file):

        raise HTTPException(
            status_code=404,
            detail="register.html file not found",
        )

    return FileResponse(register_file)


@app.get("/register.html")
async def register_html():

    register_file = os.path.join(
        BASE_DIR,
        "register.html",
    )

    if not os.path.isfile(register_file):

        raise HTTPException(
            status_code=404,
            detail="register.html file not found",
        )

    return FileResponse(register_file)


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    identifier = request.identifier.strip()
    password = request.password

    if not identifier or not password:

        return {
            "ok": False,
            "message": (
                "User ID/mobile and password are required"
            ),
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
            "message": (
                "Invalid User ID/mobile or password"
            ),
        }

    try:

        password_hasher.verify(
            user.password_hash,
            password,
        )

    except (
        VerifyMismatchError,
        VerificationError,
    ):

        return {
            "ok": False,
            "message": (
                "Invalid User ID/mobile or password"
            ),
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


# ============================================================
# REGISTER - REQUEST OTP
# ============================================================

@app.post("/register/request-otp")
async def register_request_otp(
    request: RegisterOTPRequest,
    db: Session = Depends(get_db),
):

    name = request.name.strip()
    mobile = request.mobile.strip()
    password = request.password

    if not name:

        return {
            "ok": False,
            "message": "Name is required",
        }

    if not mobile:

        return {
            "ok": False,
            "message": "Mobile number is required",
        }

    if (
        not mobile.isdigit()
        or len(mobile) != 10
    ):

        return {
            "ok": False,
            "message": (
                "Enter a valid 10-digit mobile number"
            ),
        }

    if not password:

        return {
            "ok": False,
            "message": "Password is required",
        }

    if len(password) < 6:

        return {
            "ok": False,
            "message": (
                "Password must be at least 6 characters"
            ),
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
            "message": (
                "Mobile number already registered"
            ),
        }

    otp = save_otp(
        db,
        mobile,
        "register",
    )

    return {
        "ok": True,
        "message": "OTP generated",
        "otp": otp,
        "expires_in": 120,
    }


# ============================================================
# REGISTER - VERIFY OTP
# ============================================================

@app.post("/register/verify-otp")
async def register_verify_otp(
    request: RegisterVerifyRequest,
    db: Session = Depends(get_db),
):

    mobile = request.mobile.strip()
    otp = request.otp.strip()

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == mobile,
            OTPVerification.purpose == "register",
            OTPVerification.verified == False,
        )
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message": (
                "OTP not found. Please request a new OTP"
            ),
        }

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)
        db.commit()

        return {
            "ok": False,
            "message": (
                "OTP expired. Please request a new OTP"
            ),
        }

    if verification.otp != otp:

        return {
            "ok": False,
            "message": "Invalid OTP",
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
            "message": (
                "Mobile number already registered"
            ),
        }

    user_id = (
        "UX"
        + uuid.uuid4().hex[:10]
    )

    password_hash = password_hasher.hash(
        request.password
    )

    new_user = User(
        user_id=user_id,
        name=request.name.strip(),
        mobile=mobile,
        password_hash=password_hash,
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
            "message": (
                "Registration failed. Please try again"
            ),
        }

    return {
        "ok": True,
        "message": "Registration successful",
        "user_id": new_user.user_id,
        "name": new_user.name,
        "mobile": new_user.mobile,
        "profile_photo": new_user.profile_photo,
    }


# ============================================================
# FORGOT PASSWORD - REQUEST OTP
# ============================================================

@app.post("/forgot-password/request-otp")
async def forgot_password_request_otp(
    request: ForgotOTPRequest,
    db: Session = Depends(get_db),
):

    identifier = request.identifier.strip()

    if not identifier:

        return {
            "ok": False,
            "message": (
                "User ID or mobile number is required"
            ),
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
            "message": (
                "User ID or mobile number not found"
            ),
        }

    otp = save_otp(
        db,
        user.mobile,
        "forgot_password",
    )

    return {
        "ok": True,
        "message": "OTP generated",
        "otp": otp,
        "expires_in": 120,
    }


# ============================================================
# FORGOT PASSWORD - VERIFY OTP
# ============================================================

@app.post("/forgot-password/verify-otp")
async def forgot_password_verify_otp(
    request: ForgotVerifyRequest,
    db: Session = Depends(get_db),
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
            "message": "User not found",
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == user.mobile,
            OTPVerification.purpose == "forgot_password",
            OTPVerification.verified == False,
        )
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message": (
                "OTP not found. Please request a new OTP"
            ),
        }

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)
        db.commit()

        return {
            "ok": False,
            "message": (
                "OTP expired. Please request a new OTP"
            ),
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


# ============================================================
# RESET PASSWORD
# ============================================================

@app.post("/forgot-password/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):

    identifier = request.identifier.strip()

    if len(request.new_password) < 6:

        return {
            "ok": False,
            "message": (
                "Password must be at least 6 characters"
            ),
        }

    if (
        request.new_password
        != request.confirm_password
    ):

        return {
            "ok": False,
            "message": "Passwords do not match",
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
            "message": "User not found",
        }

    verification = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == user.mobile,
            OTPVerification.purpose == "forgot_password",
            OTPVerification.verified == True,
        )
        .order_by(
            OTPVerification.id.desc()
        )
        .first()
    )

    if not verification:

        return {
            "ok": False,
            "message": (
                "OTP verification required"
            ),
        }

    if datetime.utcnow() > verification.expires_at:

        verification.verified = False

        db.commit()

        return {
            "ok": False,
            "message": (
                "OTP verification expired"
            ),
        }

    user.password_hash = password_hasher.hash(
        request.new_password
    )

    verification.verified = False

    db.commit()

    return {
        "ok": True,
        "message": (
            "Password changed successfully"
        ),
    }


# ============================================================
# FOLLOW SYSTEM
# ============================================================

@app.post("/api/follow")
async def follow_user(
    request: FollowRequest,
    db: Session = Depends(get_db),
):

    requester_id = request.requester_user_id.strip()
    target_id = request.target_user_id.strip()

    if not requester_id or not target_id:

        return {
            "ok": False,
            "message": "User IDs are required",
        }

    if requester_id == target_id:

        return {
            "ok": False,
            "message": (
                "You cannot follow your own account"
            ),
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
            "message": (
                "Requester account not found"
            ),
        }

    if not target:

        return {
            "ok": False,
            "message": "User not found",
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
            "message": (
                "You are already connected"
            ),
        }

    existing_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.requester_user_id
            == requester_id,
            ConnectionRequest.target_user_id
            == target_id,
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
                "message": (
                    "Follow request already sent"
                ),
            }

        if existing_request.status == "accepted":

            return {
                "ok": True,
                "status": "accepted",
                "message": (
                    "Request accepted. Verification required"
                ),
            }

        if existing_request.status == "verified":

            return {
                "ok": True,
                "status": "verified",
                "message": (
                    "Connection already verified"
                ),
            }

        existing_request.status = "pending"

        existing_request.updated_at = (
            datetime.utcnow()
        )

        request_row = existing_request

    else:

        request_row = ConnectionRequest(
            requester_user_id=requester_id,
            target_user_id=target_id,
            status="pending",
        )

        db.add(request_row)

        db.flush()

    notification = Notification(
        receiver_user_id=target_id,
        sender_user_id=requester_id,
        type="follow_request",
        title="New Follow Request",
        message=(
            f"{requester.name} "
            "wants to connect with you."
        ),
        connection_request_id=request_row.id,
        verification_code=None,
        is_read=False,
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
            "user_id": requester.user_id,
            "name": requester.name,
            "profile_photo": requester.profile_photo,
        },
        connection_request_id=request_row.id,
        requester_user_id=requester_id,
        target_user_id=target_id,
    )

    return {
        "ok": True,
        "status": "pending",
        "message": "Follow request sent",
        "notification_id": notification.id,
    }


# ============================================================
# CANCEL FOLLOW
# ============================================================

@app.post("/api/follow/cancel")
async def cancel_follow(
    request: FollowRequest,
    db: Session = Depends(get_db),
):

    requester_id = request.requester_user_id.strip()
    target_id = request.target_user_id.strip()

    if not requester_id or not target_id:

        return {
            "ok": False,
            "message": "User IDs are required",
        }

    connection_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.requester_user_id
            == requester_id,
            ConnectionRequest.target_user_id
            == target_id,
            ConnectionRequest.status
            == "pending",
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
            "message": "No pending request",
        }

    request_id = connection_request.id

    connection_request.status = "rejected"

    connection_request.updated_at = (
        datetime.utcnow()
    )

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
            == False,
        )
        .all()
    )

    for notification in pending_notifications:
        notification.is_read = True

    db.commit()

    await manager.send_to_user(
        target_id,
        {
            "type": "follow_cancelled",
            "requester_user_id": requester_id,
            "target_user_id": target_id,
            "connection_request_id": request_id,
        },
    )

    return {
        "ok": True,
        "status": "none",
        "message": "Follow request cancelled",
    }


# ============================================================
# FOLLOW STATUS
# ============================================================

@app.get("/api/follow/status")
async def follow_status(
    requester_user_id: str,
    target_user_id: str,
    db: Session = Depends(get_db),
):

    requester_id = requester_user_id.strip()
    target_id = target_user_id.strip()

    if not requester_id or not target_id:

        return {
            "ok": False,
            "message": "User IDs are required",
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
            "status": "verified",
        }

    row = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.requester_user_id
            == requester_id,
            ConnectionRequest.target_user_id
            == target_id,
        )
        .order_by(
            ConnectionRequest.id.desc()
        )
        .first()
    )

    if not row:

        return {
            "ok": True,
            "status": "none",
        }

    if row.status == "rejected":

        return {
            "ok": True,
            "status": "none",
        }

    return {
        "ok": True,
        "status": row.status,
    }


# ============================================================
# NOTIFICATIONS PAGE
# ============================================================

@app.get("/notifications")
async def notifications_page():

    notifications_file = os.path.join(
        BASE_DIR,
        "notifications.html",
    )

    if not os.path.isfile(notifications_file):

        raise HTTPException(
            status_code=404,
            detail=(
                "notifications.html file not found"
            ),
        )

    return FileResponse(
        notifications_file
    )


@app.get("/notifications.html")
async def notifications_html():

    notifications_file = os.path.join(
        BASE_DIR,
        "notifications.html",
    )

    if not os.path.isfile(notifications_file):

        raise HTTPException(
            status_code=404,
            detail=(
                "notifications.html file not found"
            ),
        )

    return FileResponse(
        notifications_file
    )


# ============================================================
# GET NOTIFICATIONS
# ============================================================

@app.get("/api/notifications")
async def get_notifications(
    user_id: str,
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": False,
            "message": "User ID is required",
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

        result.append(
            {
                "id": notification.id,
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "sender": {
                    "user_id": (
                        sender.user_id
                        if sender
                        else None
                    ),
                    "name": (
                        sender.name
                        if sender
                        else None
                    ),
                    "profile_photo": (
                        sender.profile_photo
                        if sender
                        else None
                    ),
                },
                "connection_request_id": (
                    notification.connection_request_id
                ),
                "verification_code": (
                    notification.verification_code
                ),
                "is_read": notification.is_read,
                "created_at": (
                    notification.created_at.isoformat()
                ),
            }
        )

    return {
        "ok": True,
        "notifications": result,
    }


# ============================================================
# ACCEPT FOLLOW REQUEST
# ============================================================

@app.post("/api/follow/accept")
async def accept_follow(
    request: ConnectionActionRequest,
    db: Session = Depends(get_db),
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id
            == request.notification_id,
            Notification.receiver_user_id
            == request.user_id,
        )
        .first()
    )

    if not notification:

        return {
            "ok": False,
            "message": "Notification not found",
        }

    if notification.type != "follow_request":

        return {
            "ok": False,
            "message": "Invalid follow request",
        }

    connection_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.id
            == notification.connection_request_id,
            ConnectionRequest.target_user_id
            == request.user_id,
        )
        .first()
    )

    if not connection_request:

        return {
            "ok": False,
            "message": (
                "Follow request not found"
            ),
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
            "message": (
                "User account not found"
            ),
        }

    if connection_request.status == "verified":

        notification.is_read = True
        db.commit()

        return {
            "ok": True,
            "status": "verified",
            "message": (
                "Connection already verified"
            ),
        }

    if connection_request.status == "accepted":

        notification.is_read = True
        db.commit()

        active_code = (
            db.query(ConnectionCode)
            .filter(
                ConnectionCode.requester_user_id
                == requester_id,
                ConnectionCode.target_user_id
                == target_id,
                ConnectionCode.verified
                == False,
                ConnectionCode.expires_at
                > datetime.utcnow(),
            )
            .order_by(
                ConnectionCode.id.desc()
            )
            .first()
        )

        if active_code:

            return {
                "ok": True,
                "status": "accepted",
                "message": (
                    "Request already accepted. "
                    "Verification code already sent"
                ),
            }

        return {
            "ok": True,
            "status": "accepted",
            "message": (
                "Request already accepted. "
                "Verification code expired"
            ),
        }

    if connection_request.status != "pending":

        return {
            "ok": False,
            "message": (
                "This request is no longer pending"
            ),
        }

    connection_request.status = "accepted"

    connection_request.updated_at = (
        datetime.utcnow()
    )

    notification.is_read = True

    active_codes = (
        db.query(ConnectionCode)
        .filter(
            ConnectionCode.requester_user_id
            == requester_id,
            ConnectionCode.target_user_id
            == target_id,
            ConnectionCode.verified
            == False,
        )
        .all()
    )

    for old_code in active_codes:
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
        verified=False,
    )

    db.add(connection_code)

    requester_notification = Notification(
        receiver_user_id=requester_id,
        sender_user_id=target_id,
        type="connection_code",
        title="Connection Accepted",
        message=(
            f"{target.name} accepted your "
            f"connection request. "
            f"Your verification code is {code}."
        ),
        connection_request_id=(
            connection_request.id
        ),
        verification_code=code,
        is_read=False,
    )

    db.add(requester_notification)

    db.commit()

    db.refresh(
        requester_notification
    )

    await push_notification(
        requester_id,
        "connection_code",
        requester_notification.id,
        requester_notification.title,
        requester_notification.message,
        sender={
            "user_id": target.user_id,
            "name": target.name,
            "profile_photo": target.profile_photo,
        },
        connection_request_id=(
            connection_request.id
        ),
        verification_code=code,
        requester_user_id=requester_id,
        target_user_id=target_id,
    )

    return {
        "ok": True,
        "status": "accepted",
        "message": (
            "Request accepted. Verification code sent"
        ),
    }


# ============================================================
# REJECT FOLLOW REQUEST
# ============================================================

@app.post("/api/follow/reject")
async def reject_follow(
    request: ConnectionActionRequest,
    db: Session = Depends(get_db),
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id
            == request.notification_id,
            Notification.receiver_user_id
            == request.user_id,
        )
        .first()
    )

    if not notification:

        return {
            "ok": False,
            "message": "Notification not found",
        }

    if notification.type != "follow_request":

        return {
            "ok": False,
            "message": "Invalid follow request",
        }

    connection_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.id
            == notification.connection_request_id,
            ConnectionRequest.target_user_id
            == request.user_id,
        )
        .first()
    )

    if not connection_request:

        return {
            "ok": False,
            "message": (
                "Follow request not found"
            ),
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

    if connection_request.status == "verified":

        notification.is_read = True
        db.commit()

        return {
            "ok": True,
            "status": "verified",
            "message": (
                "Connection is already verified"
            ),
        }

    connection_request.status = "rejected"

    connection_request.updated_at = (
        datetime.utcnow()
    )

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
        connection_request_id=(
            connection_request.id
        ),
        verification_code=None,
        is_read=False,
    )

    db.add(requester_notification)

    db.commit()

    db.refresh(
        requester_notification
    )

    await push_notification(
        requester_id,
        "follow_rejected",
        requester_notification.id,
        requester_notification.title,
        requester_notification.message,
        sender={
            "user_id": (
                target.user_id
                if target
                else target_id
            ),
            "name": (
                target.name
                if target
                else target_id
            ),
            "profile_photo": (
                target.profile_photo
                if target
                else None
            ),
        },
        connection_request_id=(
            connection_request.id
        ),
        requester_user_id=requester_id,
        target_user_id=target_id,
    )

    return {
        "ok": True,
        "status": "rejected",
        "message": (
            "Follow request rejected"
        ),
    }


# ============================================================
# VERIFY CONNECTION CODE
# ============================================================

@app.post("/api/follow/verify")
async def verify_connection(
    request: VerifyConnectionCodeRequest,
    db: Session = Depends(get_db),
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
            "message": "User IDs are required",
        }

    if not code:

        return {
            "ok": False,
            "message": (
                "Verification code is required"
            ),
        }

    connection_request = (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.requester_user_id
            == requester_id,
            ConnectionRequest.target_user_id
            == target_id,
        )
        .order_by(
            ConnectionRequest.id.desc()
        )
        .first()
    )

    if not connection_request:

        return {
            "ok": False,
            "message": (
                "Connection request not found"
            ),
        }

    if connection_request.status == "verified":

        return {
            "ok": True,
            "status": "verified",
            "message": (
                "Connection already verified"
            ),
        }

    if connection_request.status != "accepted":

        return {
            "ok": False,
            "message": (
                "Connection has not been accepted"
            ),
        }

    connection_code = (
        db.query(ConnectionCode)
        .filter(
            ConnectionCode.requester_user_id
            == requester_id,
            ConnectionCode.target_user_id
            == target_id,
            ConnectionCode.verified
            == False,
        )
        .order_by(
            ConnectionCode.id.desc()
        )
        .first()
    )

    if not connection_code:

        return {
            "ok": False,
            "message": (
                "Verification code not found "
                "or already used"
            ),
        }

    if datetime.utcnow() > connection_code.expires_at:

        connection_code.verified = True
        db.commit()

        return {
            "ok": False,
            "message": (
                "Verification code expired"
            ),
        }

    if connection_code.code != code:

        return {
            "ok": False,
            "message": (
                "Invalid verification code"
            ),
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

    if not requester or not target:

        return {
            "ok": False,
            "message": (
                "User account not found"
            ),
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

    connection_code.verified = True

    connection_request.status = "verified"

    connection_request.updated_at = (
        datetime.utcnow()
    )

    if not existing_connection:

        new_connection = Connection(
            user_a_id=requester_id,
            user_b_id=target_id,
        )

        db.add(new_connection)

    target_notification = Notification(
        receiver_user_id=target_id,
        sender_user_id=requester_id,
        type="connection_verified",
        title="Connection Verified",
        message=(
            f"You are now connected with "
            f"{requester.name}."
        ),
        connection_request_id=(
            connection_request.id
        ),
        verification_code=None,
        is_read=False,
    )

    requester_notification = Notification(
        receiver_user_id=requester_id,
        sender_user_id=target_id,
        type="connection_verified",
        title="Connection Verified",
        message=(
            f"You are now connected with "
            f"{target.name}."
        ),
        connection_request_id=(
            connection_request.id
        ),
        verification_code=None,
        is_read=False,
    )

    db.add(target_notification)
    db.add(requester_notification)

    try:

        db.commit()

    except IntegrityError:

        db.rollback()

        return {
            "ok": False,
            "message": (
                "Connection verification failed"
            ),
        }

    db.refresh(
        target_notification
    )

    db.refresh(
        requester_notification
    )

    await push_notification(
        target_id,
        "connection_verified",
        target_notification.id,
        target_notification.title,
        target_notification.message,
        sender={
            "user_id": requester.user_id,
            "name": requester.name,
            "profile_photo": requester.profile_photo,
        },
        connection_request_id=(
            connection_request.id
        ),
        requester_user_id=requester_id,
        target_user_id=target_id,
    )

    await push_notification(
        requester_id,
        "connection_verified",
        requester_notification.id,
        requester_notification.title,
        requester_notification.message,
        sender={
            "user_id": target.user_id,
            "name": target.name,
            "profile_photo": target.profile_photo,
        },
        connection_request_id=(
            connection_request.id
        ),
        requester_user_id=requester_id,
        target_user_id=target_id,
    )

    return {
        "ok": True,
        "status": "verified",
        "message": (
            "Connection verified successfully"
        ),
    }


# ============================================================
# MARK NOTIFICATION READ
# ============================================================

@app.post("/api/notifications/read")
async def mark_notification_read(
    request: NotificationReadRequest,
    db: Session = Depends(get_db),
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id
            == request.notification_id,
            Notification.receiver_user_id
            == request.user_id,
        )
        .first()
    )

    if not notification:

        return {
            "ok": False,
            "message": "Notification not found",
        }

    notification.is_read = True

    db.commit()

    return {
        "ok": True,
        "message": (
            "Notification marked as read"
        ),
    }


# ============================================================
# MARK ALL NOTIFICATIONS READ
# ============================================================

@app.post("/api/notifications/read-all")
async def mark_all_notifications_read(
    user_id: str,
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": False,
            "message": "User ID is required",
        }

    notifications = (
        db.query(Notification)
        .filter(
            Notification.receiver_user_id
            == user_id,
            Notification.is_read
            == False,
        )
        .all()
    )

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return {
        "ok": True,
        "message": (
            "All notifications marked as read"
        ),
        "count": len(notifications),
    }


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/home")
async def home_page():

    home_file = os.path.join(
        BASE_DIR,
        "home.html",
    )

    if not os.path.isfile(home_file):

        raise HTTPException(
            status_code=404,
            detail="home.html file not found",
        )

    return FileResponse(
        home_file
    )


# ============================================================
# PROFILE API
# ============================================================

@app.get("/api/profile/{user_id}")
async def get_profile(
    user_id: str,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.user_id == user_id.strip()
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "ok": True,
        "profile": {
            "user_id": user.user_id,
            "name": user.name,
            "profile_photo": user.profile_photo
        }
    }


# ============================================================
# PROFILE PHOTO UPLOAD - CLOUDINARY
# ============================================================

@app.post("/api/profile/{user_id}/photo")
async def upload_profile_photo(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()

    if not user_id:

        raise HTTPException(
            status_code=400,
            detail="User ID is required",
        )

    user = (
        db.query(User)
        .filter(
            User.user_id == user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not file.content_type:

        raise HTTPException(
            status_code=400,
            detail="Invalid image",
        )

    if not file.content_type.startswith("image/"):

        raise HTTPException(
            status_code=400,
            detail="Please select an image",
        )

    try:

        result = cloudinary.uploader.upload(
            file.file,
            folder="usanex/profile_photos",
            public_id=user_id,
            overwrite=True,
            resource_type="image",
            secure=True,
        )

    except Exception as e:

        print(
            "Cloudinary upload error:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Profile photo upload failed",
        )

    profile_photo_url = result.get(
        "secure_url"
    )

    if not profile_photo_url:

        raise HTTPException(
            status_code=500,
            detail="Cloudinary image URL not received",
        )

    user.profile_photo = profile_photo_url

    db.commit()
    db.refresh(user)

    return {
        "ok": True,
        "message": "Profile photo saved",
        "profile_photo": user.profile_photo,
    }


# ============================================================
# PROFILE PAGE
# ============================================================

@app.get("/profile")
async def profile_page():

    profile_file = os.path.join(
        BASE_DIR,
        "profile.html",
    )

    if not os.path.isfile(profile_file):

        raise HTTPException(
            status_code=404,
            detail="profile.html file not found",
        )

    return FileResponse(
        profile_file
    )


# ============================================================
# HOME CONNECTIONS
# ============================================================

@app.get("/api/home/connections")
async def home_connections(
    user_id: str = "",
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": True,
            "users": [],
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

        users.append(
            {
                "user_id": user.user_id,
                "name": user.name,
                "profile_photo": user.profile_photo,
                "profile_picture": user.profile_photo,
            }
        )

    return {
        "ok": True,
        "users": users,
    }


# ============================================================
# HOME CONNECTIONS - COMPATIBILITY ROUTE
# ============================================================

@app.get("/api/connections")
async def get_connections(
    user_id: str = "",
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": True,
            "connections": [],
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

        users.append(
            {
                "user_id": user.user_id,
                "name": user.name,
                "profile_photo": user.profile_photo,
                "profile_picture": user.profile_photo,
            }
        )

    return {
        "ok": True,
        "connections": users,
    }


# ============================================================
# CHAT PAGE
# ============================================================

@app.get("/chat")
async def chat_page():

    chat_file = os.path.join(
        BASE_DIR,
        "chat.html",
    )

    if not os.path.isfile(chat_file):

        raise HTTPException(
            status_code=404,
            detail="chat.html file not found",
        )

    return FileResponse(
        chat_file
    )


@app.get("/chat.html")
async def chat_html():

    chat_file = os.path.join(
        BASE_DIR,
        "chat.html",
    )

    if not os.path.isfile(chat_file):

        raise HTTPException(
            status_code=404,
            detail="chat.html file not found",
        )

    return FileResponse(
        chat_file
    )


# ============================================================
# CHAT CONNECTION CHECK
# ============================================================

def are_connected(
    db: Session,
    user_a: str,
    user_b: str,
):

    return (
        db.query(Connection)
        .filter(
            (
                (Connection.user_a_id == user_a)
                &
                (Connection.user_b_id == user_b)
            )
            |
            (
                (Connection.user_a_id == user_b)
                &
                (Connection.user_b_id == user_a)
            )
        )
        .first()
        is not None
    )


# ============================================================
# GET CHAT MESSAGES
# ============================================================

@app.get("/api/chat/messages")
async def get_chat_messages(
    user_id: str,
    other_user_id: str,
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()
    other_user_id = other_user_id.strip()

    if not user_id or not other_user_id:

        raise HTTPException(
            status_code=400,
            detail="User IDs are required",
        )

    if user_id == other_user_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid chat",
        )

    if not are_connected(
        db,
        user_id,
        other_user_id,
    ):

        raise HTTPException(
            status_code=403,
            detail="You can chat only with connected users",
        )

    other = (
        db.query(User)
        .filter(
            User.user_id == other_user_id
        )
        .first()
    )

    if not other:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    messages = (
        db.query(ChatMessage)
        .filter(
            (
                (ChatMessage.sender_user_id == user_id)
                &
                (ChatMessage.receiver_user_id == other_user_id)
            )
            |
            (
                (ChatMessage.sender_user_id == other_user_id)
                &
                (ChatMessage.receiver_user_id == user_id)
            )
        )
        .order_by(
            ChatMessage.id.asc()
        )
        .limit(200)
        .all()
    )

    return {
        "ok": True,
        "other_user": {
            "user_id": other.user_id,
            "name": other.name,
            "profile_photo": other.profile_photo,
        },
        "messages": [
            {
                "id": message.id,
                "sender_user_id": message.sender_user_id,
                "receiver_user_id": message.receiver_user_id,
                "message": message.message,
                "message_type": message.message_type,
                "is_read": message.is_read,
                "created_at": (
                    message.created_at.isoformat()
                ),
            }
            for message in messages
        ],
    }


# ============================================================
# SEND CHAT MESSAGE
# ============================================================

@app.post("/api/chat/send")
async def send_chat_message(
    request: SendMessageRequest,
    db: Session = Depends(get_db),
):

    sender_id = request.sender_user_id.strip()
    receiver_id = request.receiver_user_id.strip()
    text = request.message.strip()

    if not sender_id or not receiver_id:

        raise HTTPException(
            status_code=400,
            detail="User IDs are required",
        )

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    if len(text) > 5000:

        raise HTTPException(
            status_code=400,
            detail="Message is too long",
        )

    if sender_id == receiver_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid chat",
        )

    sender = (
        db.query(User)
        .filter(
            User.user_id == sender_id
        )
        .first()
    )

    receiver = (
        db.query(User)
        .filter(
            User.user_id == receiver_id
        )
        .first()
    )

    if not sender or not receiver:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not are_connected(
        db,
        sender_id,
        receiver_id,
    ):

        raise HTTPException(
            status_code=403,
            detail="You can chat only with connected users",
        )

    new_message = ChatMessage(
        sender_user_id=sender_id,
        receiver_user_id=receiver_id,
        message=text,
        message_type="text",
        is_read=False,
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    message_data = {
        "type": "chat_message",
        "message": {
            "id": new_message.id,
            "sender_user_id": sender_id,
            "receiver_user_id": receiver_id,
            "message": new_message.message,
            "message_type": new_message.message_type,
            "is_read": new_message.is_read,
            "created_at": (
                new_message.created_at.isoformat()
            ),
        },
    }

    await manager.send_to_user(
        receiver_id,
        message_data,
    )

    return {
        "ok": True,
        **message_data,
    }


# ============================================================
# MARK CHAT MESSAGES AS READ
# ============================================================

@app.post("/api/chat/read")
async def mark_chat_read(
    user_id: str,
    other_user_id: str,
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()
    other_user_id = other_user_id.strip()

    if not user_id or not other_user_id:

        raise HTTPException(
            status_code=400,
            detail="User IDs are required",
        )

    if not are_connected(
        db,
        user_id,
        other_user_id,
    ):

        raise HTTPException(
            status_code=403,
            detail="Not connected",
        )

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.sender_user_id == other_user_id,
            ChatMessage.receiver_user_id == user_id,
            ChatMessage.is_read == False,
        )
        .all()
    )

    for message in messages:
        message.is_read = True

    db.commit()

    return {
        "ok": True,
        "count": len(messages),
    }


# ============================================================
# REELS PAGE
# ============================================================

@app.get("/reels")
async def reels_page():

    reels_file = os.path.join(
        BASE_DIR,
        "reels.html",
    )

    if not os.path.isfile(reels_file):

        raise HTTPException(
            status_code=404,
            detail="reels.html file not found",
        )

    return FileResponse(
        reels_file
    )


# ============================================================
# STATUS PAGE
# ============================================================

@app.get("/status")
async def status_page():

    return FileResponse(
        os.path.join(
            BASE_DIR,
            "status.html"
        )
    )


@app.get("/status.html")
async def status_html_page():

    return FileResponse(
        os.path.join(
            BASE_DIR,
            "status.html"
        )
    )


# ============================================================
# STATUS UPLOAD - CLOUDINARY
# ============================================================

@app.post("/api/status/upload")
async def upload_status(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    user_id = user_id.strip()

    if not user_id:

        raise HTTPException(
            status_code=400,
            detail="User ID is required",
        )

    # --------------------------------------------------------
    # CHECK USER
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.user_id == user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # --------------------------------------------------------
    # CHECK FILE TYPE
    # --------------------------------------------------------

    content_type = file.content_type or ""

    if content_type.startswith("image/"):

        media_type = "image"
        resource_type = "image"

    elif content_type.startswith("video/"):

        media_type = "video"
        resource_type = "video"

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only image and video files are allowed."
            ),
        )

    # --------------------------------------------------------
    # CLOUDINARY UPLOAD
    # --------------------------------------------------------

    try:

        result = cloudinary.uploader.upload(
            file.file,
            folder=f"usanex/status/{user_id}",
            resource_type=resource_type,
            secure=True,
        )

    except Exception as e:

        print(
            "Cloudinary status upload error:",
            str(e),
        )

        raise HTTPException(
            status_code=500,
            detail="Cloudinary status upload failed",
        )

    media_url = result.get(
        "secure_url"
    )

    if not media_url:

        raise HTTPException(
            status_code=500,
            detail="Cloudinary URL not received",
        )

    # --------------------------------------------------------
    # STATUS TIME
    # --------------------------------------------------------

    created_at = datetime.utcnow()

    expires_at = (
        created_at
        + timedelta(hours=24)
    )

    # --------------------------------------------------------
    # SAVE STATUS TO DATABASE
    # --------------------------------------------------------

    new_status = Status(
        user_id=user_id,
        media_url=media_url,
        media_type=media_type,
        created_at=created_at,
        expires_at=expires_at,
    )

    try:

        db.add(new_status)

        db.commit()

        db.refresh(new_status)

    except Exception as e:

        db.rollback()

        print(
            "Status database error:",
            str(e),
        )

        raise HTTPException(
            status_code=500,
            detail="Status record could not be saved",
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "ok": True,
        "message": "Status uploaded successfully",

        "status": {
            "id": new_status.id,
            "user_id": new_status.user_id,
            "media_url": new_status.media_url,
            "media_type": new_status.media_type,
            "created_at": (
                new_status.created_at.isoformat()
            ),
            "expires_at": (
                new_status.expires_at.isoformat()
            ),
        },
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    return {
        "ok": True,
        "status": "online",
        "app": "Usanex",
        "realtime": "websocket",
    }


# ============================================================
# LOCAL RUN
# ============================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.getenv(
            "PORT",
            "8000",
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )
