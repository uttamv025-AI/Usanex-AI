from fastapi import FastAPI, Depends
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from datetime import datetime, timedelta

import secrets
import uuid
import os


from database import SessionLocal, User, OTPVerification


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

    return FileResponse(
        search_file
    )


# ============================================================
# SEARCH API
# USER ID OR MOBILE NUMBER
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

            (User.user_id.ilike(
                f"%{q}%"
            ))

            |

            (User.mobile.ilike(
                f"%{q}%"
            ))

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

    return FileResponse(

        os.path.join(
            BASE_DIR,
            "register.html"
        )

    )


@app.get("/register.html")
async def register_html():

    return FileResponse(

        os.path.join(
            BASE_DIR,
            "register.html"
        )

    )


# ============================================================
# LOGIN API
# USER ID OR MOBILE NUMBER
# ============================================================

@app.post("/login")
async def login(

    request: LoginRequest,

    db: Session = Depends(get_db)

):

    identifier = request.identifier.strip()

    password = request.password

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not identifier or not password:

        return {

            "ok": False,

            "message":
            "Username/mobile and password are required"

        }

    # --------------------------------------------------------
    # FIND USER BY USER ID OR MOBILE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VERIFY PASSWORD
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TEMPORARY LOGIN TOKEN
    # --------------------------------------------------------

    token = secrets.token_urlsafe(32)

    return {

        "ok": True,

        "message":
        "Login successful",

        "token":
        token,

        "user": {

            "user_id":
            user.user_id,

            "name":
            user.name,

            "mobile":
            user.mobile

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

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    if not name:

        return {

            "ok": False,

            "message":
            "Name is required"

        }

    # --------------------------------------------------------
    # MOBILE
    # --------------------------------------------------------

    if not mobile:

        return {

            "ok": False,

            "message":
            "Mobile number is required"

        }

    if not mobile.isdigit() or len(mobile) != 10:

        return {

            "ok": False,

            "message":
            "Enter a valid 10-digit mobile number"

        }

    # --------------------------------------------------------
    # PASSWORD
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CHECK EXISTING USER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # GENERATE OTP
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FIND OTP
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # OTP EXPIRY
    # --------------------------------------------------------

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)

        db.commit()

        return {

            "ok": False,

            "message":
            "OTP expired. Please request a new OTP"

        }

    # --------------------------------------------------------
    # OTP CHECK
    # --------------------------------------------------------

    if verification.otp != otp:

        return {

            "ok": False,

            "message":
            "Invalid OTP"

        }

    # --------------------------------------------------------
    # CHECK USER AGAIN
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CREATE USER ID
    # --------------------------------------------------------

    user_id = (

        "UX"
        +
        uuid.uuid4().hex[:10]

    )

    # --------------------------------------------------------
    # HASH PASSWORD
    # --------------------------------------------------------

    password_hash = (

        password_hasher.hash(
            request.password
        )

    )

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return {

        "ok": True,

        "message":
        "Registration successful",

        "user_id":
        new_user.user_id,

        "name":
        new_user.name,

        "mobile":
        new_user.mobile

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

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not identifier:

        return {

            "ok": False,

            "message":
            "User ID or mobile number is required"

        }

    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # GENERATE OTP
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FIND OTP
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # EXPIRY
    # --------------------------------------------------------

    if datetime.utcnow() > verification.expires_at:

        db.delete(verification)

        db.commit()

        return {

            "ok": False,

            "message":
            "OTP expired. Please request a new OTP"

        }

    # --------------------------------------------------------
    # CHECK OTP
    # --------------------------------------------------------

    if verification.otp != otp:

        return {

            "ok": False,

            "message":
            "Invalid OTP"

        }

    # --------------------------------------------------------
    # MARK VERIFIED
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PASSWORD LENGTH
    # --------------------------------------------------------

    if len(request.new_password) < 6:

        return {

            "ok": False,

            "message":
            "Password must be at least 6 characters"

        }

    # --------------------------------------------------------
    # PASSWORD MATCH
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FIND VERIFIED OTP
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CHECK OTP EXPIRY
    # --------------------------------------------------------

    if datetime.utcnow() > verification.expires_at:

        verification.verified = False

        db.commit()

        return {

            "ok": False,

            "message":
            "OTP verification expired"

        }

    # --------------------------------------------------------
    # CHANGE PASSWORD
    # --------------------------------------------------------

    user.password_hash = (

        password_hasher.hash(
            request.new_password
        )

    )

    # --------------------------------------------------------
    # OTP CAN ONLY BE USED ONCE
    # --------------------------------------------------------

    verification.verified = False

    db.commit()

    return {

        "ok": True,

        "message":
        "Password changed successfully"

    }


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/home")
async def home_page():

    return FileResponse(

        os.path.join(
            BASE_DIR,
            "home.html"
        )

    )


# ============================================================
# HOME CONNECTIONS
# ============================================================

@app.get("/api/home/connections")
async def home_connections(

    db: Session = Depends(get_db)

):

    # --------------------------------------------------------
    # CONNECTION SYSTEM ABHI NAHI BANAYA GAYA HAI
    # --------------------------------------------------------

    return {

        "ok": True,

        "users": []

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
