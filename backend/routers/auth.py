from fastapi import APIRouter, HTTPException

from schemas.auth import LoginRequest, LoginResponse
from services.data_loader import load_users

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    """
    開発用モックログイン。本番では JWT 等に差し替え予定。
    デモ: teacher@example.com / admin@example.com （パスワード: demo）
    """
    users = load_users()
    match = next(
        (
            u
            for u in users
            if u["email"].lower() == str(body.email).lower() and u["password"] == body.password
        ),
        None,
    )
    if match is None:
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")

    role = match["role"]
    teacher_id = match.get("teacher_id")
    token_suffix = teacher_id if teacher_id is not None else "admin"
    return LoginResponse(
        token=f"mock-token-{token_suffix}",
        role=role,
        teacher_id=teacher_id,
        name=match["name"],
        redirect=match["redirect"],
    )
