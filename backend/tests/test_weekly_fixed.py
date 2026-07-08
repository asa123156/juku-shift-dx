"""通常授業の同一曜日展開テスト。"""

from datetime import date

from services.assignment_grid import manual_assign
from services.assignment_store import get_assignments_for_date, reset_assignments_for_tests
from services.entity_store import create_teacher, reset_entities_for_tests
from services.period_bootstrap import bootstrap_period_dashboards
from services.period_store import create_period, open_dates_for_period, reset_periods_for_tests


def _setup_period():
    reset_periods_for_tests()
    reset_entities_for_tests()
    teacher = create_teacher("テスト講師")
    period = create_period("曜日展開テスト", "2026-06-09", "2026-06-20", [])
    bootstrap_period_dashboards(period.id)
    return period, teacher


def _tuesdays_in_period(period) -> list[str]:
    return [
        iso_date
        for iso_date in open_dates_for_period(period)
        if date.fromisoformat(iso_date).weekday() == 1
    ]


def test_fixed_schedule_repeats_on_same_weekday():
    reset_assignments_for_tests()
    period, teacher = _setup_period()
    tuesdays = _tuesdays_in_period(period)
    assert len(tuesdays) >= 2

    manual_assign(
        tuesdays[0],
        1,
        "山田太郎",
        "数学",
        teacher["id"],
        2,
        skip_rules=True,
        is_fixed=True,
        period_id=period.id,
    )

    for iso_date in tuesdays:
        rows = [
            r
            for r in get_assignments_for_date(iso_date)
            if r["teacher_id"] == teacher["id"] and r["slot"] == 2 and r["is_fixed"]
        ]
        assert len(rows) == 1
        assert rows[0]["subject"] == "数学"
        assert rows[0]["student_name"] == "山田太郎"

    wednesday = next(
        iso_date
        for iso_date in open_dates_for_period(period)
        if date.fromisoformat(iso_date).weekday() == 2
    )
    wed_rows = get_assignments_for_date(wednesday)
    assert not any(r["teacher_id"] == teacher["id"] and r["slot"] == 2 for r in wed_rows)


def test_fixed_schedule_updates_all_matching_weekdays():
    reset_assignments_for_tests()
    period, teacher = _setup_period()
    tuesdays = _tuesdays_in_period(period)

    manual_assign(
        tuesdays[0],
        1,
        "山田太郎",
        "数学",
        teacher["id"],
        2,
        skip_rules=True,
        is_fixed=True,
        period_id=period.id,
    )
    manual_assign(
        tuesdays[0],
        1,
        "山田太郎",
        "英語",
        teacher["id"],
        2,
        skip_rules=True,
        is_fixed=True,
        period_id=period.id,
    )

    for iso_date in tuesdays:
        rows = get_assignments_for_date(iso_date)
        fixed = [r for r in rows if r["teacher_id"] == teacher["id"] and r["slot"] == 2]
        assert len(fixed) == 1
        assert fixed[0]["subject"] == "英語"
