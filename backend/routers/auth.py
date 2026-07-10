from fastapi import APIRouter, HTTPException

from schemas.auth import LoginRequest, LoginResponse
from security import create_access_token, verify_password
from services.data_loader import load_users

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    """
    デモ: teacher@example.com / admin@example.com （パスワード: demo）
    """
    users = load_users()
    match = next(
        (u for u in users if u["email"].lower() == str(body.email).lower()),
        None,
    )
    if match is None or not verify_password(body.password, match["password"]):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")

    role = match["role"]
    teacher_id = match.get("teacher_id")
    student_id = match.get("student_id")
    token = create_access_token(
        {
            "sub": match["email"],
            "role": role,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "name": match["name"],
        }
    )
    return LoginResponse(
        token=token,
        role=role,
        teacher_id=teacher_id,
        student_id=student_id,
        name=match["name"],
        redirect=match["redirect"],
    )
