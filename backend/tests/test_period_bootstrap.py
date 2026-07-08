"""講習期間ダッシュボードと講師マスタの同期テスト。"""

from database import SessionLocal
from models import Period as PeriodRow
from models import ShiftDashboard as ShiftDashboardRow
from models import TeacherProfile
from services.assignment_grid import build_assignment_grid
from services.entity_store import create_teacher, reset_entities_for_tests
from services.period_bootstrap import bootstrap_period_dashboards, sync_teacher_to_all_period_dashboards
from services.period_store import create_period


def _clean_period_and_dashboards() -> None:
    with SessionLocal() as db:
        db.query(ShiftDashboardRow).delete()
        db.query(PeriodRow).delete()
        db.commit()
    reset_entities_for_tests()


def test_new_teacher_appears_on_assignment_grid() -> None:
    _clean_period_and_dashboards()

    period = create_period("同期テスト講習", "2026-06-09", "2026-06-11", [])
    bootstrap_period_dashboards(period.id)

    grid_before = build_assignment_grid("2026-06-09")
    count_before = len(grid_before["teachers"])

    teacher = create_teacher("追加講師")

    grid_after = build_assignment_grid("2026-06-09")
    assert len(grid_after["teachers"]) == count_before + 1
    assert any(t["id"] == teacher["id"] and t["name"] == "追加講師" for t in grid_after["teachers"])


def test_sync_teacher_to_all_period_dashboards() -> None:
    _clean_period_and_dashboards()

    period = create_period("手動同期テスト", "2026-06-09", "2026-06-10", [])
    bootstrap_period_dashboards(period.id)

    with SessionLocal() as db:
        row = TeacherProfile(name="手動追加", color="bg-amber-100 text-amber-600")
        db.add(row)
        db.commit()
        db.refresh(row)
        manual_id = row.id

    added = sync_teacher_to_all_period_dashboards(manual_id)
    assert added >= 1

    grid = build_assignment_grid("2026-06-09")
    assert manual_id in {t["id"] for t in grid["teachers"]}
