from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    sender_user_id: str = Field(min_length=1)
    receiver_user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ReadMessagesRequest(BaseModel):
    user_id: str = Field(min_length=1)
    other_user_id: str = Field(min_length=1)
