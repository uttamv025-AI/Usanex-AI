from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect
)
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
import json

from database import (
    SessionLocal,
    User,
    OTPVerification,
    ConnectionRequest,
    ConnectionCode,
    Notification,
    Connection,
    ChatMessage
)


# ============================================================
# APP
# ============================================================

app = FastAPI(title="Usanex")

password_hasher = PasswordHasher()


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


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


class ChatMessageRequest(BaseModel):
    sender_user_id: str
    receiver_user_id: str
    message: str


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

    old = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.identifier == identifier,
            OTPVerification.purpose == purpose
        )
        .all()
    )

    for item in old:
        db.delete(item)

    row = OTPVerification(
        identifier=identifier,
        otp=otp,
        purpose=purpose,
        expires_at=datetime.utcnow()
        + timedelta(minutes=2),
        verified=False
    )

    db.add(row)
    db.commit()

    return otp


# ============================================================
# LOGIN API
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
                "Username/mobile and password are required"
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
                "Invalid username/mobile or password"
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
                "Invalid username/mobile or password"
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
# LOGIN PAGE
# ============================================================

@app.get("/")
async def root_page():

    login_file = os.path.join(
        BASE_DIR,
        "login.html"
    )

    if not os.path.isfile(login_file):

        raise HTTPException(
            status_code=404,
            detail="login.html file not found"
        )

    return FileResponse(login_file)


@app.get("/login")
async def login_page():

    login_file = os.path.join(
        BASE_DIR,
        "login.html"
    )

    if not os.path.isfile(login_file):

        raise HTTPException(
            status_code=404,
            detail="login.html file not found"
        )

    return FileResponse(login_file)


@app.get("/login.html")
async def login_html():

    login_file = os.path.join(
        BASE_DIR,
        "login.html"
    )

    if not os.path.isfile(login_file):

        raise HTTPException(
            status_code=404,
            detail="login.html file not found"
        )

    return FileResponse(login_file)


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

    if (
        not mobile.isdigit()
        or len(mobile) != 10
    ):

        return {
            "ok": False,
            "message":
                "Enter a valid 10-digit mobile number"
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
            "message": "Invalid OTP"
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
        +
        uuid.uuid4().hex[:10]
    )

    password_hash = (
        password_hasher.hash(
            request.password
        )
    )

    new_user = User(
        user_id=user_id,
        name=name,
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
        "user_id": new_user.user_id,
        "name": new_user.name,
        "mobile": new_user.mobile
    }


# ============================================================
# REGISTER PAGE
# ============================================================

@app.get("/register")
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
# FORGOT PASSWORD - REQUEST OTP
# ============================================================

@app.post("/forgot-password/request-otp")
async def forgot_password_request_otp(
    request: ForgotOTPRequest,
    db: Session = Depends(get_db)
):

    identifier = request.identifier.strip()

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
            (User.user_id == identifier)
            |
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
            "message": "User not found"
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
# CONNECTION CHECK
# ============================================================

def are_users_connected(
    db: Session,
    user_a_id: str,
    user_b_id: str
) -> bool:

    user_a_id = user_a_id.strip()
    user_b_id = user_b_id.strip()

    if not user_a_id or not user_b_id:

        return False

    if user_a_id == user_b_id:

        return False

    connection = (
        db.query(Connection)
        .filter(
            (
                (Connection.user_a_id == user_a_id)
                &
                (Connection.user_b_id == user_b_id)
            )
            |
            (
                (Connection.user_a_id == user_b_id)
                &
                (Connection.user_b_id == user_a_id)
            )
        )
        .first()
    )

    return connection is not None


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

        profile_photo = getattr(
            user,
            "profile_photo",
            None
        )

        users.append({
            "user_id": user.user_id,
            "name": user.name,
            "profile_photo": profile_photo,
            "profile_picture": profile_photo
        })

    return {
        "ok": True,
        "users": users
    }


# ============================================================
# CONNECTIONS API
# ============================================================

@app.get("/api/connections")
async def connections_api(
    user_id: str = "",
    db: Session = Depends(get_db)
):

    user_id = user_id.strip()

    if not user_id:

        return {
            "ok": True,
            "connections": []
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

    result = []
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

        profile_photo = getattr(
            user,
            "profile_photo",
            None
        )

        result.append({
            "user_id": user.user_id,
            "name": user.name,
            "profile_photo": profile_photo,
            "profile_picture": profile_photo
        })

    return {
        "ok": True,
        "connections": result
    }


# ============================================================
# CHAT CONNECTION MANAGER
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

            if (
                user_id
                not in self.active_connections
            ):

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

            if (
                user_id
                not in self.active_connections
            ):

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
# PUSH NOTIFICATION
# ============================================================

async def push_notification(
    user_id: str,
    data: dict
):

    await manager.send_to_user(
        user_id,
        data
    )


# ============================================================
# CHAT HISTORY
# ============================================================

@app.get("/api/chat/history")
async def chat_history(
    user_id: str,
    other_user_id: str,
    db: Session = Depends(get_db)
):

    user_id = user_id.strip()
    other_user_id = other_user_id.strip()

    if not user_id or not other_user_id:

        return {
            "ok": False,
            "message": "User IDs are required"
        }

    if not are_users_connected(
        db,
        user_id,
        other_user_id
    ):

        return {
            "ok": False,
            "connected": False,
            "message":
                "Chat is available only for connected users"
        }

    messages = (
        db.query(ChatMessage)
        .filter(
            (
                (ChatMessage.sender_user_id == user_id)
                &
                (
                    ChatMessage.receiver_user_id
                    == other_user_id
                )
            )
            |
            (
                (
                    ChatMessage.sender_user_id
                    == other_user_id
                )
                &
                (
                    ChatMessage.receiver_user_id
                    == user_id
                )
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
        "connected": True,
        "messages": [
            {
                "id": message.id,
                "sender_user_id":
                    message.sender_user_id,
                "receiver_user_id":
                    message.receiver_user_id,
                "message":
                    message.message,
                "message_type":
                    message.message_type,
                "is_read":
                    message.is_read,
                "created_at":
                    message.created_at.isoformat()
            }

            for message in messages
        ]
    }


# ============================================================
# HTTP CHAT SEND
# ============================================================

@app.post("/api/chat/send")
async def send_chat_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db)
):

    sender_id = (
        request.sender_user_id.strip()
    )

    receiver_id = (
        request.receiver_user_id.strip()
    )

    text = request.message.strip()

    if not sender_id or not receiver_id:

        return {
            "ok": False,
            "message": "User IDs are required"
        }

    if sender_id == receiver_id:

        return {
            "ok": False,
            "message":
                "You cannot chat with yourself"
        }

    if not text:

        return {
            "ok": False,
            "message":
                "Message cannot be empty"
        }

    if len(text) > 5000:

        return {
            "ok": False,
            "message":
                "Message is too long"
        }

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

    if not sender:

        return {
            "ok": False,
            "message":
                "Sender account not found"
        }

    if not receiver:

        return {
            "ok": False,
            "message":
                "Receiver account not found"
        }

    if not are_users_connected(
        db,
        sender_id,
        receiver_id
    ):

        return {
            "ok": False,
            "connected": False,
            "message":
                "You can chat only with connected users"
        }

    new_message = ChatMessage(
        sender_user_id=sender_id,
        receiver_user_id=receiver_id,
        message=text,
        message_type="text",
        is_read=False
    )

    db.add(new_message)

    db.commit()

    db.refresh(new_message)

    message_data = {
        "id": new_message.id,
        "sender_user_id": sender_id,
        "receiver_user_id": receiver_id,
        "message": new_message.message,
        "message_type": new_message.message_type,
        "is_read": False,
        "created_at":
            new_message.created_at.isoformat()
    }

    realtime_data = {
        "type": "chat_message",
        "message": message_data
    }

    await manager.send_to_user(
        receiver_id,
        realtime_data
    )

    await manager.send_to_user(
        sender_id,
        realtime_data
    )

    return {
        "ok": True,
        "connected": True,
        "message": message_data
    }


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

        await websocket.close(
            code=1008
        )

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

                raw_data = (
                    await websocket.receive_text()
                )

                if raw_data == "ping":

                    await websocket.send_json({
                        "type": "pong",
                        "timestamp":
                            datetime.utcnow()
                            .isoformat()
                    })

                    continue

                try:

                    data = json.loads(
                        raw_data
                    )

                except json.JSONDecodeError:

                    continue

                if not isinstance(data, dict):

                    continue

                message_type = data.get(
                    "type"
                )

                # ==================================================
                # REAL-TIME CHAT MESSAGE
                # ==================================================

                if message_type == "chat_message":

                    sender_id = str(
                        data.get(
                            "sender_user_id",
                            ""
                        )
                    ).strip()

                    receiver_id = str(
                        data.get(
                            "receiver_user_id",
                            ""
                        )
                    ).strip()

                    text = str(
                        data.get(
                            "message",
                            ""
                        )
                    ).strip()

                    # Sender MUST match websocket user
                    if sender_id != user_id:

                        await websocket.send_json({
                            "type":
                                "chat_error",
                            "message":
                                "Sender identity mismatch"
                        })

                        continue

                    if not receiver_id:

                        await websocket.send_json({
                            "type":
                                "chat_error",
                            "message":
                                "Receiver user ID is required"
                        })

                        continue

                    if sender_id == receiver_id:

                        await websocket.send_json({
                            "type":
                                "chat_error",
                            "message":
                                "You cannot chat with yourself"
                        })

                        continue

                    if not text:

                        await websocket.send_json({
                            "type":
                                "chat_error",
                            "message":
                                "Message cannot be empty"
                        })

                        continue

                    if len(text) > 5000:

                        await websocket.send_json({
                            "type":
                                "chat_error",
                            "message":
                                "Message is too long"
                        })

                        continue

                    chat_db = SessionLocal()

                    try:

                        sender = (
                            chat_db.query(User)
                            .filter(
                                User.user_id
                                == sender_id
                            )
                            .first()
                        )

                        receiver = (
                            chat_db.query(User)
                            .filter(
                                User.user_id
                                == receiver_id
                            )
                            .first()
                        )

                        if not sender:

                            await websocket.send_json({
                                "type":
                                    "chat_error",
                                "message":
                                    "Sender account not found"
                            })

                            continue

                        if not receiver:

                            await websocket.send_json({
                                "type":
                                    "chat_error",
                                "message":
                                    "Receiver account not found"
                            })

                            continue

                        # ==================================================
                        # CONNECTED USERS ONLY
                        # ==================================================

                        if not are_users_connected(
                            chat_db,
                            sender_id,
                            receiver_id
                        ):

                            await websocket.send_json({
                                "type":
                                    "chat_error",
                                "connected":
                                    False,
                                "message":
                                    "You can chat only with connected users"
                            })

                            continue

                        new_message = ChatMessage(
                            sender_user_id=
                                sender_id,
                            receiver_user_id=
                                receiver_id,
                            message=text,
                            message_type=
                                "text",
                            is_read=False
                        )

                        chat_db.add(
                            new_message
                        )

                        chat_db.commit()

                        chat_db.refresh(
                            new_message
                        )

                        message_data = {
                            "id":
                                new_message.id,
                            "sender_user_id":
                                sender_id,
                            "receiver_user_id":
                                receiver_id,
                            "message":
                                new_message.message,
                            "message_type":
                                new_message.message_type,
                            "is_read":
                                False,
                            "created_at":
                                new_message.created_at
                                .isoformat()
                        }

                    except Exception:

                        chat_db.rollback()

                        await websocket.send_json({
                            "type":
                                "chat_error",
                            "message":
                                "Message could not be saved"
                        })

                        continue

                    finally:

                        chat_db.close()

                    realtime_data = {
                        "type":
                            "chat_message",
                        "message":
                            message_data
                    }

                    # Send to receiver
                    await manager.send_to_user(
                        receiver_id,
                        realtime_data
                    )

                    # Send to sender
                    await manager.send_to_user(
                        sender_id,
                        realtime_data
                    )

                    continue

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
# CHAT PAGE
# ============================================================

@app.get("/chat")
async def chat_page():

    chat_file = os.path.join(
        BASE_DIR,
        "chat.html"
    )

    if not os.path.isfile(chat_file):

        raise HTTPException(
            status_code=404,
            detail="chat.html file not found"
        )

    return FileResponse(
        chat_file
    )


@app.get("/chat.html")
async def chat_html():

    chat_file = os.path.join(
        BASE_DIR,
        "chat.html"
    )

    if not os.path.isfile(chat_file):

        raise HTTPException(
            status_code=404,
            detail="chat.html file not found"
        )

    return FileResponse(
        chat_file
    )


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

    return FileResponse(
        home_file
    )


@app.get("/home.html")
async def home_html():

    home_file = os.path.join(
        BASE_DIR,
        "home.html"
    )

    if not os.path.isfile(home_file):

        raise HTTPException(
            status_code=404,
            detail="home.html file not found"
        )

    return FileResponse(
        home_file
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
            detail="search.html file not found"
        )

    return FileResponse(
        search_file
    )


@app.get("/search.html")
async def search_html():

    search_file = os.path.join(
        BASE_DIR,
        "search.html"
    )

    if not os.path.isfile(search_file):

        raise HTTPException(
            status_code=404,
            detail="search.html file not found"
        )

    return FileResponse(
        search_file
    )


# ============================================================
# NOTIFICATIONS PAGE
# ============================================================

@app.get("/notifications")
async def notifications_page():

    notifications_file = os.path.join(
        BASE_DIR,
        "notifications.html"
    )

    if not os.path.isfile(
        notifications_file
    ):

        raise HTTPException(
            status_code=404,
            detail=
                "notifications.html file not found"
        )

    return FileResponse(
        notifications_file
    )


@app.get("/notifications.html")
async def notifications_html():

    notifications_file = os.path.join(
        BASE_DIR,
        "notifications.html"
    )

    if not os.path.isfile(
        notifications_file
    ):

        raise HTTPException(
            status_code=404,
            detail=
                "notifications.html file not found"
        )

    return FileResponse(
        notifications_file
    )


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
# RUN
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
