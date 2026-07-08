"""年度（4月始まり）と REGULAR Period のテスト。"""

from datetime import date

import pytest

from services.academic_calendar import fiscal_year_bounds, fiscal_year_for_date, open_dates_for_calendar_month
from services.fiscal_year_store import ensure_fiscal_regular_period, find_regular_period_for_fiscal_year
from services.period_store import create_period, find_cram_period_for_date, find_period_for_date, reset_periods_for_tests
from services.schedule_context import resolve_schedule_context, tutoring_period_id_for_date
from services.schedule_service import assert_proposal_received, build_my_schedule


@pytest.fixture(autouse=True)
def clean_periods():
    reset_periods_for_tests()
    yield


def test_fiscal_year_for_date():
    assert fiscal_year_for_date("2026-03-31") == 2025
    assert fiscal_year_for_date("2026-04-01") == 2026


def test_ensure_fiscal_regular_period():
    period = ensure_fiscal_regular_period(2026)
    start, end = fiscal_year_bounds(2026)
    assert period.name == "2026年度"
    assert period.start_date == start
    assert period.end_date == end
    assert period.period_kind == "REGULAR"
    assert find_regular_period_for_fiscal_year(2026) is not None


def test_find_period_prefers_cram():
    regular = ensure_fiscal_regular_period(2026)
    cram = create_period("夏期講習", "2026-07-20", "2026-08-31")
    assert find_cram_period_for_date("2026-08-01").id == cram.id
    assert find_period_for_date("2026-08-01").id == cram.id
    assert find_period_for_date("2026-05-10").id == regular.id


def test_schedule_context_regular_vs_cram():
    regular = ensure_fiscal_regular_period(2026)
    from services.period_store import set_active_period, update_period_status

    set_active_period(regular.id)
    ctx_regular = resolve_schedule_context("2026-05-10")
    assert ctx_regular["mode"] == "regular"
    assert ctx_regular["period_id"] == regular.id

    cram = create_period("夏期", "2026-07-20", "2026-08-31", closed_dates=[])
    update_period_status(cram.id, "COLLECTING")
    set_active_period(cram.id)
    ctx_cram = resolve_schedule_context("2026-08-01")
    assert ctx_cram["mode"] == "cram"
    assert ctx_cram["period_id"] == cram.id
    assert ctx_cram["regular_period_id"] == regular.id


def test_schedule_context_uses_active_cram_when_today_outside_period():
    ensure_fiscal_regular_period(2026)
    cram = create_period("6月講習", "2026-06-09", "2026-06-20")
    from services.period_store import set_active_period, update_period_status

    update_period_status(cram.id, "COLLECTING")
    set_active_period(cram.id)
    assert find_cram_period_for_date("2026-07-08") is None
    ctx = resolve_schedule_context("2026-07-08")
    assert ctx["mode"] == "cram"
    assert ctx["period_id"] == cram.id


def test_tutoring_period_id_for_date():
    regular = ensure_fiscal_regular_period(2026)
    cram = create_period("夏期", "2026-07-20", "2026-08-31")
    from services.period_store import update_period_status

    update_period_status(cram.id, "COLLECTING")
    assert tutoring_period_id_for_date("2026-08-01", regular.id) == cram.id
    assert tutoring_period_id_for_date("2026-05-01", regular.id) == regular.id


def test_regular_schedule_skips_proposal_gate():
    period = ensure_fiscal_regular_period(2026)
    assert_proposal_received("student", 1, period.id)
    sched = build_my_schedule("student", 1, period.id, calendar_year=2026, month=5)
    assert sched["period_kind"] == "REGULAR"
    assert sched["schedule_requested"] is False
    assert len(sched["dates"]) == len(open_dates_for_calendar_month(2026, 5, period.closed_dates))
