"""slot_capacity_store のテスト。"""

import pytest
from fastapi import HTTPException

from services.slot_capacity_store import get_max_lanes, lesson_format_label, set_max_lanes


def test_lesson_format_label() -> None:
    assert lesson_format_label(2) == "1対2"
    assert lesson_format_label(4) == "1対4"


def test_set_and_get_max_lanes() -> None:
    set_max_lanes(99, "2026-06-15", 1, 4, avail="", assignments=[])
    assert get_max_lanes(99, "2026-06-15", 1) == 4


def test_cannot_shrink_when_assignments_overflow() -> None:
    assigns = [
        {"student_id": 1, "student_name": "A", "subject": "数学", "lesson_kind": "講習"},
        {"student_id": 2, "student_name": "B", "subject": "英語", "lesson_kind": "講習"},
        {"student_id": 3, "student_name": "C", "subject": "国語", "lesson_kind": "講習"},
    ]
    with pytest.raises(HTTPException) as exc:
        set_max_lanes(98, "2026-06-16", 2, 2, avail="", assignments=assigns)
    assert exc.value.status_code == 409
