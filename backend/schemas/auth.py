from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    token: str
    role: Literal["teacher", "admin"]
    teacher_id: int | None = None
    name: str
    redirect: str
