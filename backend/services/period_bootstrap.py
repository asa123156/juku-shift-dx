"""講習（Period）作成時にダッシュボード（紙の日付範囲）を生成する。"""

from datetime import date

from fastapi import HTTPException

from services.dashboard_store import upsert_shift_dashboard
from services.entity_store import list_teachers
from services.period_store import get_period, open_dates_for_period
from services.slot_timing import SLOT_FIELDS, generate_time_slots

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


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
    if not teachers:
        teachers = [_default_teacher_row({"id": 1, "name": "講師（未登録）", "color": "bg-gray-100 text-gray-600"})]

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
            continue
        existing_ids = {t["id"] for t in dash.get("teachers", [])}
        teachers = list(dash.get("teachers", []))
        changed = False
        for tid in teacher_ids:
            if tid in existing_ids:
                continue
            meta = teachers_meta.get(tid)
            if meta is None:
                continue
            teachers.append(_default_teacher_row(meta))
            added_rows += 1
            changed = True
        if changed:
            upsert_shift_dashboard({**dash, "teachers": teachers})
    return added_rows
