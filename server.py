from fastapi import FastAPI, Depends
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from argon2 import PasswordHasher
import os
import uuid

from database import SessionLocal, User


app = FastAPI(title="Usanex AI")

password_hasher = PasswordHasher()


class RegisterRequest(BaseModel):
    name: str
    mobile: str
    password: str


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@app.post("/register")
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    name = request.name.strip()
    mobile = request.mobile.strip()
    password = request.password

    # Basic validation
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

    if not password:
        return {
            "ok": False,
            "message": "Password is required"
        }

    if len(password) < 6:
        return {
            "ok": False,
            "message": "Password must be at least 6 characters"
        }

    # Check existing mobile
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
    user_id = "UX" + uuid.uuid4().hex[:10]

    # Hash password
    password_hash = password_hasher.hash(password)

    # Create user
    new_user = User(
        user_id=user_id,
        name=name,
        mobile=mobile,
        password_hash=password_hash
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()

        return {
            "ok": False,
            "message": "Registration failed. Please try again."
        }

    return {
        "ok": True,
        "message": "Registration successful",
        "user_id": new_user.user_id,
        "name": new_user.name,
        "mobile": new_user.mobile
    }


@app.get("/")
async def home():
    return FileResponse("index.html")


@app.get("/health")
async def health():
    return {
        "ok": True,
        "status": "online",
        "app": "Usanex AI"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
