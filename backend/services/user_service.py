from sqlalchemy.orm import Session

from backend.models import User


# =========================================================
# SEARCH USERS
# =========================================================

def search_users(
    db: Session,
    query: str,
):
    """
    Search users by name or User ID.
    """

    query = query.strip()

    if not query:
        return []

    search_pattern = f"%{query}%"

    users = (
        db.query(User)
        .filter(
            (User.name.ilike(search_pattern))
            | (User.user_id.ilike(search_pattern))
        )
        .order_by(User.name.asc())
        .limit(50)
        .all()
    )

    return [
        {
            "user_id": user.user_id,
            "name": user.name,
            "mobile": user.mobile,
            "profile_photo": user.profile_photo,
        }
        for user in users
    ]


# =========================================================
# GET USER PROFILE
# =========================================================

def get_user_profile(
    db: Session,
    user_id: str,
):
    """
    Get a user's public profile information.
    """

    user_id = user_id.strip()

    if not user_id:
        return None

    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        return None

    return {
        "user_id": user.user_id,
        "name": user.name,
        "mobile": user.mobile,
        "profile_photo": user.profile_photo,
    }
