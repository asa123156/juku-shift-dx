from fastapi import APIRouter

from schemas.lessons import LessonRow
from services.data_loader import load_lessons

router = APIRouter(prefix="/api", tags=["lessons"])


@router.get("/lessons", response_model=list[LessonRow])
def get_lessons() -> list[LessonRow]:
    """
    授業コマ割り（講師・生徒・科目）の一覧を返す。
    データ源: docs/lesson_mock.json
    """
    rows = load_lessons()
    return [LessonRow.model_validate(row) for row in rows]
