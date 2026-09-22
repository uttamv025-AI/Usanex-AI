from pydantic import BaseModel


class UserResponse(BaseModel):
    user_id: str
    name: str
    mobile: str
    profile_photo: str | None = None


class ProfilePhotoResponse(BaseModel):
    user_id: str
    profile_photo: str
