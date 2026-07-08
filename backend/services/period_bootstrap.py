"""講習（Period）作成時にダッシュボード（紙の日付範囲）を生成する。"""

from datetime import date

from fastapi import HTTPException

from services.dashboard_store import upsert_shift_dashboard
from services.entity_store import list_teachers
from services.period_store import get_period, open_dates_for_period
from services.slot_timing import SLOT_FIELDS, generate_time_slots

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]
PLACEHOLDER_TEACHER_NAME = "講師（未登録）"


def _default_teacher_row(meta: dict) -> dict:
    row = {"id": meta["id"], "name": meta["name"], "color": meta["color"]}
    for i, field in enumerate(SLOT_FIELDS):
        row[field] = "未提出" if i == len(SLOT_FIELDS) - 1 else "待機"
    return row


def bootstrap_period_dashboards(period_id: int) -> int:
    """開校日（日曜除く）分のシフトダッシュボードを作成する。"""
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    time_slots = generate_time_slots()
    teachers = [_default_teacher_row(t) for t in list_teachers()]

    for iso_date in open_dates:
        d = date.fromisoformat(iso_date)
        display = f"{d.year}年 {d.month}月{d.day}日 ({WEEKDAY_JA[d.weekday()]}) の状況"
        upsert_shift_dashboard(
            {
                "date": iso_date,
                "display_date": display,
                "time_slots": time_slots,
                "teachers": teachers,
            }
        )
    return len(open_dates)


def _dashboard_shell(iso_date: str) -> dict:
    d = date.fromisoformat(iso_date)
    display = f"{d.year}年 {d.month}月{d.day}日 ({WEEKDAY_JA[d.weekday()]}) の状況"
    return {
        "date": iso_date,
        "display_date": display,
        "time_slots": generate_time_slots(),
        "teachers": [],
    }


def _merge_teacher_row(existing: dict, meta: dict) -> dict:
    """ダッシュボード行の名前・色を更新し、提出済みコマは維持する。"""
    row = _default_teacher_row(meta)
    for field in SLOT_FIELDS:
        prev = existing.get(field)
        if prev not in (None, "", "待機", "未提出"):
            row[field] = prev
    return row


def _strip_placeholder_teachers(teachers: list[dict]) -> list[dict]:
    return [t for t in teachers if t.get("name") != PLACEHOLDER_TEACHER_NAME]


def add_teachers_to_period_dashboards(period_id: int, teacher_ids: list[int]) -> int:
    """開校日ダッシュボードに講師行がなければ追加する。"""
    if not teacher_ids:
        return 0
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    teachers_meta = {t["id"]: t for t in list_teachers()}
    added_rows = 0

    from services.dashboard_store import load_shift_dashboard_base, upsert_shift_dashboard

    for iso_date in open_dates:
        try:
            dash = load_shift_dashboard_base(iso_date)
        except HTTPException:
            dash = _dashboard_shell(iso_date)
        teachers = list(dash.get("teachers", []))
        existing_ids = {t["id"] for t in teachers}
        changed = False
        for tid in teacher_ids:
            meta = teachers_meta.get(tid)
            if meta is None:
                continue
            if tid in existing_ids:
                for idx, row in enumerate(teachers):
                    if row.get("id") != tid:
                        continue
                    merged = _merge_teacher_row(row, meta)
                    if merged != row:
                        teachers[idx] = merged
                        changed = True
                continue
            teachers = _strip_placeholder_teachers(teachers)
            existing_ids = {t["id"] for t in teachers}
            if tid in existing_ids:
                continue
            teachers.append(_default_teacher_row(meta))
            added_rows += 1
            changed = True
        if changed:
            upsert_shift_dashboard({**dash, "teachers": teachers})
    return added_rows


def sync_teacher_to_all_period_dashboards(teacher_id: int) -> int:
    """全講習期間の開校日ダッシュボードに講師を反映する（時間割表の列に出す）。"""
    from services.period_store import list_periods

    periods, _ = list_periods()
    total = 0
    for period in periods:
        total += add_teachers_to_period_dashboards(period.id, [teacher_id])
    return total
