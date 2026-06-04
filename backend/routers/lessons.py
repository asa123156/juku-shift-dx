from typing import Annotated

from fastapi import APIRouter, Query

from schemas.lessons import LessonRow
from services.data_loader import load_lessons

router = APIRouter(prefix="/api", tags=["lessons"])


@router.get("/lessons", response_model=list[LessonRow])
def get_lessons(
    date: Annotated[
        str | None,
        Query(description="YYYY-MM-DD で授業を絞り込み"),
    ] = None,
) -> list[LessonRow]:
    rows = load_lessons(date=date)
    return [LessonRow.model_validate(row) for row in rows]
