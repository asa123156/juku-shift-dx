from fastapi import APIRouter, Depends, HTTPException, Request

from dependencies import CurrentUser, get_current_user
from schemas.auth import ChangePasswordRequest, ChangePasswordResponse, LoginRequest, LoginResponse
from security import create_access_token, verify_password
from services.data_loader import load_users
from services.rate_limit import check_login_allowed, record_attempt

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request) -> LoginResponse:
    client_ip = request.client.host if request.client else "unknown"
    blocked = check_login_allowed(client_ip, str(body.email))
    if blocked:
        message, retry_after = blocked
        raise HTTPException(
            status_code=429, detail=message, headers={"Retry-After": str(retry_after)}
        )

    users = load_users()
    match = next(
        (u for u in users if u["email"].lower() == str(body.email).lower()),
        None,
    )
    if match is None or not verify_password(body.password, match["password"]):
        record_attempt(client_ip, str(body.email), success=False)
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")

    record_attempt(client_ip, str(body.email), success=True)
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


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ChangePasswordResponse:
    from services.entity_store import change_user_password

    change_user_password(user.email, body.current_password, body.new_password)
    return ChangePasswordResponse(message="パスワードを変更しました")
