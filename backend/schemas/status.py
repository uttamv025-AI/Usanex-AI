from pydantic import BaseModel, Field


class StatusViewRequest(BaseModel):
    status_id: int = Field(gt=0)
    viewer_user_id: str = Field(min_length=1)
