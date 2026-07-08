"""手動 is_fixed 登録のテスト。"""

from services.assignment_grid import manual_assign
from services.assignment_store import get_assignments_for_date, reset_assignments_for_tests
from services.entity_store import create_teacher, reset_entities_for_tests
from services.period_bootstrap import bootstrap_period_dashboards
from services.period_store import create_period, reset_periods_for_tests


def _setup_period():
    reset_periods_for_tests()
    reset_entities_for_tests()
    teacher = create_teacher("テスト講師")
    period = create_period("通常授業テスト", "2026-06-09", "2026-06-11", [])
    bootstrap_period_dashboards(period.id)
    return period, teacher


def test_manual_assign_fixed():
    reset_assignments_for_tests()
    period, teacher = _setup_period()
    manual_assign(
        period.start_date,
        1,
        "山田太郎",
        "",
        teacher["id"],
        2,
        skip_rules=True,
        is_fixed=True,
        period_id=period.id,
    )
    rows = get_assignments_for_date(period.start_date)
    fixed = [r for r in rows if r["slot"] == 2 and r["student_id"] == 1]
    assert len(fixed) == 1
    assert fixed[0]["is_fixed"] is True
    assert fixed[0]["lesson_kind"] == "通常"
    assert fixed[0]["subject"] == "通常"


def test_manual_assign_fixed_with_subject():
    reset_assignments_for_tests()
    period, teacher = _setup_period()
    manual_assign(
        period.start_date,
        1,
        "山田太郎",
        "数学",
        teacher["id"],
        3,
        skip_rules=True,
        is_fixed=True,
        period_id=period.id,
    )
    rows = get_assignments_for_date(period.start_date)
    fixed = [r for r in rows if r["slot"] == 3 and r["student_id"] == 1]
    assert len(fixed) == 1
    assert fixed[0]["subject"] == "数学"
    assert fixed[0]["is_fixed"] is True
