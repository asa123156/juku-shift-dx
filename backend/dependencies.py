from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from security import decode_access_token


class CurrentUser(BaseModel):
    email: str
    role: str
    teacher_id: int | None = None
    student_id: int | None = None
    name: str


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認証トークンがありません")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="認証トークンの有効期限が切れています")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="認証トークンが不正です")
    return CurrentUser(
        email=payload["sub"],
        role=payload["role"],
        teacher_id=payload.get("teacher_id"),
        student_id=payload.get("student_id"),
        name=payload.get("name", ""),
    )


def require_admin(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="この操作には教室長権限が必要です")
    return current_user


def assert_self_or_admin(current_user: CurrentUser, role: str, entity_id: int) -> None:
    if current_user.role == "admin":
        return
    own_id = current_user.teacher_id if current_user.role == "teacher" else current_user.student_id
    if current_user.role != role or own_id != entity_id:
        raise HTTPException(status_code=403, detail="他のユーザーのデータは操作できません")
