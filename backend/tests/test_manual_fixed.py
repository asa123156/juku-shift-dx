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


def test_manual_assign_other_is_fixed_single_date():
    """「その他」（体験・振替など）: 固定枠扱いだが毎週展開されず、その日だけ登録される。"""
    reset_assignments_for_tests()
    period, teacher = _setup_period()
    manual_assign(
        period.start_date,
        1,
        "山田太郎",
        "算数",
        teacher["id"],
        4,
        skip_rules=True,
        is_fixed=False,  # フロントの other モードは is_fixed=False + lesson_type で送る
        period_id=period.id,
        lesson_type="体験",
    )
    rows = get_assignments_for_date(period.start_date)
    other = [r for r in rows if r["slot"] == 4 and r["student_id"] == 1]
    assert len(other) == 1
    assert other[0]["is_fixed"] is True  # ロック挙動は通常授業と同じ
    assert other[0]["lesson_type"] == "体験"
    assert other[0]["subject"] == "算数"

    # 毎週展開されていないこと（開始日以外の開校日に増えていない）
    for iso in ("2026-06-10", "2026-06-11"):
        others = [
            r for r in get_assignments_for_date(iso) if r["slot"] == 4 and r["student_id"] == 1
        ]
        assert others == []
