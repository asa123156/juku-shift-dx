"""講師の提案書送付フローのテスト。"""

from services.schedule_publish_store import (
    is_teacher_schedule_request_published,
    publish_teacher_schedule_request,
)
from services.schedule_service import build_my_schedule


def test_teacher_schedule_request_gates_view():
    if not is_teacher_schedule_request_published(1, 1):
        assert publish_teacher_schedule_request(1, 1) is True
    assert is_teacher_schedule_request_published(1, 1) is True
    assert publish_teacher_schedule_request(1, 1) is False

    schedule = build_my_schedule("teacher", 1, 1)
    assert schedule["schedule_requested"] is True
