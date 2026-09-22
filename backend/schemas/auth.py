from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterOTPRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=6)


class RegisterVerifyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=6)
    otp: str = Field(min_length=1, max_length=10)


class ForgotOTPRequest(BaseModel):
    identifier: str = Field(min_length=1)


class ForgotVerifyRequest(BaseModel):
    identifier: str = Field(min_length=1)
    otp: str = Field(min_length=1, max_length=10)


class ResetPasswordRequest(BaseModel):
    identifier: str = Field(min_length=1)
    new_password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)
