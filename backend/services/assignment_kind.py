"""割当レコードの授業種別（通常 / 講習）を class_schedules から判定。"""

from services.class_schedule_store import get_schedules_for_date


def infer_is_fixed(iso_date: str, teacher_id: int, slot: int) -> bool:
    for row in get_schedules_for_date(iso_date, fixed_only=True):
        if row["teacher_id"] == teacher_id and row["slot"] == slot:
            return True
    from services.availability_dashboard import build_availability_dashboard

    REGULAR = frozenset({"◎", "通常授業"})
    dashboard = build_availability_dashboard(iso_date)
    teacher_row = next((t for t in dashboard.get("teachers", []) if t["id"] == teacher_id), None)
    if teacher_row is None:
        return False
    return teacher_row.get(f"s{slot}", "") in REGULAR


def infer_lesson_kind(iso_date: str, teacher_id: int, slot: int) -> str:
    return "通常" if infer_is_fixed(iso_date, teacher_id, slot) else "講習"
