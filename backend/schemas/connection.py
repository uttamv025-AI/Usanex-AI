from pydantic import BaseModel, Field


class FollowRequest(BaseModel):
    requester_user_id: str = Field(min_length=1)
    target_user_id: str = Field(min_length=1)


class FollowCancelRequest(BaseModel):
    requester_user_id: str = Field(min_length=1)
    target_user_id: str = Field(min_length=1)


class FollowActionRequest(BaseModel):
    target_user_id: str = Field(min_length=1)


class ConnectionVerifyRequest(BaseModel):
    requester_user_id: str = Field(min_length=1)
    target_user_id: str = Field(min_length=1)
    code: str = Field(min_length=1, max_length=20)
