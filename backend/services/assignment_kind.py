"""割当レコードの授業種別（通常 / 講習）を講師コマから推定。"""

REGULAR_TEACHER_AVAIL = frozenset({"◎", "通常授業"})


def infer_lesson_kind(iso_date: str, teacher_id: int, slot: int) -> str:
    from services.availability_dashboard import build_availability_dashboard

    dashboard = build_availability_dashboard(iso_date)
    row = next((t for t in dashboard.get("teachers", []) if t["id"] == teacher_id), None)
    if row is None:
        return "講習"
    avail = row.get(f"s{slot}", "")
    return "通常" if avail in REGULAR_TEACHER_AVAIL else "講習"
