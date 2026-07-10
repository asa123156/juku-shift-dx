from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    token: str
    role: Literal["teacher", "admin", "student"]
    teacher_id: int | None = None
    student_id: int | None = None
    name: str
    redirect: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, description="8文字以上")


class ChangePasswordResponse(BaseModel):
    message: str
