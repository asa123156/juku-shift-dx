"""期間単位の割当シート（日曜除外・複数日）を組み立てる。"""

from copy import deepcopy
from datetime import date

from services.assignment_store import get_assignment_requests_for_date, get_assignments_for_date
from services.teacher_slot_lanes import build_teacher_lanes, teacher_slot_assignable
from services.availability_dashboard import build_availability_dashboard
from services.entity_store import get_student_name_map, list_students
from services.period_store import get_period, open_dates_for_period
from services.schedule_publish_store import list_published_student_ids, list_published_teacher_ids
from services.student_plan_store import list_plans_for_period
from services.slot_timing import SLOT_NUMS, generate_time_slots
from services.submission_store import get_submissions_for_date
from schemas.period import empty_slots


from services.student_slot_codec import student_availability_label


def _student_availability(symbol: str) -> str:
    return student_availability_label(symbol)


def _collect_student_registry(open_dates: list[str]) -> dict[int, dict]:
    registry = {s["id"]: dict(s) for s in list_students()}
    names = get_student_name_map()
    for iso_date in open_dates:
        for row in get_assignment_requests_for_date(iso_date):
            sid = row["student_id"]
            if sid not in registry:
                registry[sid] = {
                    "id": sid,
                    "name": row["student_name"],
                    "school_level": "",
                    "grade_year": 0,
                    "grade_label": "",
                    "level_label": "",
                }
            else:
                registry[sid]["name"] = row["student_name"]
        for row in get_assignments_for_date(iso_date):
            sid = row["student_id"]
            if sid not in registry:
                registry[sid] = {
                    "id": sid,
                    "name": row["student_name"],
                    "school_level": "",
                    "grade_year": 0,
                    "grade_label": "",
                    "level_label": "",
                }
        for sid in get_submissions_for_date("student", iso_date):
            if sid not in registry:
                registry[sid] = {
                    "id": sid,
                    "name": names.get(sid, f"生徒{sid}"),
                    "school_level": "",
                    "grade_year": 0,
                    "grade_label": "",
                    "level_label": "",
                }
    return registry


def _build_student_day(iso_date: str, student_id: int, assignments: list[dict], pending: list[dict]) -> dict:
    subs = get_submissions_for_date("student", iso_date).get(student_id, empty_slots())
    assign_by_slot = {a["slot"]: a for a in assignments if a["student_id"] == student_id}
    pending_subjects = list({r["subject"] for r in pending if r["student_id"] == student_id})
    slots = []
    for slot_num in SLOT_NUMS:
        symbol = subs.get(str(slot_num), "")
        slots.append(
            {
                "slot": slot_num,
                "availability": _student_availability(symbol),
                "assignment": assign_by_slot.get(slot_num),
            }
        )
    return {"slots": slots, "pending_subjects": pending_subjects}


def _build_teacher_day(iso_date: str, teacher_id: int, teacher_row: dict, assignments: list[dict]) -> dict:
    assign_by_slot: dict[int, list] = {}
    for a in assignments:
        if a["teacher_id"] == teacher_id:
            assign_by_slot.setdefault(a["slot"], []).append(a)
    slots = []
    for slot_num in SLOT_NUMS:
        avail = teacher_row.get(f"s{slot_num}", "")
        at_slot = assign_by_slot.get(slot_num, [])
        lanes = build_teacher_lanes(avail, at_slot)
        slots.append(
            {
                "slot": slot_num,
                "availability": avail,
                "assignable": teacher_slot_assignable(avail, at_slot),
                "lanes": lanes,
                "assignments": at_slot,
                "assignment": at_slot[0] if at_slot else None,
            }
        )
    return {"slots": slots}


def build_assignment_sheets(period_id: int) -> dict:
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    time_slots = generate_time_slots()

    registry = _collect_student_registry(open_dates)
    published_ids = list_published_student_ids(period_id)
    teacher_published_ids = list_published_teacher_ids(period_id)
    plans_by_student = list_plans_for_period(period_id)
    students = []
    for sid in sorted(registry):
        meta = registry[sid]
        subject_plans = plans_by_student.get(sid, [])
        days: dict[str, dict] = {}
        total_pending = 0
        subjects: set[str] = set()
        for iso_date in open_dates:
            assignments = get_assignments_for_date(iso_date)
            pending = get_assignment_requests_for_date(iso_date)
            day = _build_student_day(iso_date, sid, assignments, pending)
            days[iso_date] = day
            total_pending += len([r for r in pending if r["student_id"] == sid])
            subjects.update(day["pending_subjects"])
        students.append(
            {
                "id": sid,
                "name": meta["name"],
                "school_level": meta.get("school_level", ""),
                "grade_year": meta.get("grade_year", 0),
                "grade_label": meta.get("grade_label", ""),
                "level_label": meta.get("level_label", ""),
                "days": days,
                "pending_count": total_pending,
                "subjects": [p["subject"] for p in subject_plans],
                "subject_plans": subject_plans,
                "schedule_published": sid in published_ids,
            }
        )

    # 講師は最初の開校日の一覧をベースに id を揃える
    teacher_meta: dict[int, dict] = {}
    if open_dates:
        first = build_availability_dashboard(open_dates[0])
        for t in first.get("teachers", []):
            teacher_meta[t["id"]] = {"id": t["id"], "name": t["name"], "color": t.get("color", "")}

    teachers = []
    for tid in sorted(teacher_meta):
        meta = teacher_meta[tid]
        days: dict[str, dict] = {}
        for iso_date in open_dates:
            dash = build_availability_dashboard(iso_date)
            row = next((t for t in dash["teachers"] if t["id"] == tid), None)
            if row is None:
                continue
            assignments = get_assignments_for_date(iso_date)
            days[iso_date] = _build_teacher_day(iso_date, tid, row, assignments)
        teachers.append({**meta, "days": days, "schedule_published": tid in teacher_published_ids})

    pending_by_date: dict[str, list] = {}
    all_pending = 0
    for iso_date in open_dates:
        pending = get_assignment_requests_for_date(iso_date)
        pending_by_date[iso_date] = deepcopy(pending)
        all_pending += len(pending)

    date_labels = []
    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    for iso_date in open_dates:
        d = date.fromisoformat(iso_date)
        date_labels.append(
            {
                "date": iso_date,
                "label": f"{d.month}/{d.day}",
                "weekday": weekday_names[d.weekday()],
            }
        )

    return {
        "period_id": period.id,
        "period_name": period.name,
        "period_status": period.status,
        "dates": date_labels,
        "time_slots": time_slots,
        "students": students,
        "teachers": teachers,
        "pending_by_date": pending_by_date,
        "pending_total": all_pending,
    }
