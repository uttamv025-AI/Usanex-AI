from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.services.user_service import (
    search_users,
    get_user_profile,
)


router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)


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
# SEARCH USERS
# =========================================================

@router.get("/search")
async def search(
    q: str,
    db: Session = Depends(get_db),
):
    """
    Search users by name or User ID.
    """

    users = search_users(
        db=db,
        query=q,
    )

    return {
        "ok": True,
        "users": users,
    }


# =========================================================
# GET USER PROFILE
# =========================================================

@router.get("/{user_id}")
async def profile(
    user_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a user's profile.
    """

    user = get_user_profile(
        db=db,
        user_id=user_id,
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return {
        "ok": True,
        "user": user,
    }
