"""講習期間・生徒・講師マスタをすべて削除する（教室長ログインのみ残す）。

Usage:
    cd backend && python -m scripts.clear_masters
"""

from __future__ import annotations

import json
from pathlib import Path

from config import DATA_DIR
from database import SessionLocal, init_db
from models import (
    AdminOverride,
    AppSetting,
    Assignment,
    AssignmentRequest,
    ClassSchedule,
    Period,
    PeriodBaseSlot,
    PeriodScheduleWorkbook,
    ShiftChangeRequest,
    ShiftDashboard,
    ShiftSubmission,
    StudentProfile,
    StudentSchedulePublish,
    StudentScheduleRequestPublish,
    StudentSubjectPlan,
    TeacherProfile,
    TeacherSchedulePublish,
    TeacherScheduleRequestPublish,
    TeacherSlotCapacity,
)
from scripts.clear_schedules import clear_schedule_json_files


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clear_master_json_files() -> None:
    clear_schedule_json_files()
    _write_json(DATA_DIR / "periods.json", {"next_id": 1, "active_period_id": None, "items": []})
    _write_json(DATA_DIR / "period-bases.json", {})
    _write_json(DATA_DIR / "students.json", {"next_id": 1, "items": []})
    _write_json(DATA_DIR / "teachers.json", {"next_id": 1, "items": []})

    users_path = DATA_DIR / "users.json"
    users = json.loads(users_path.read_text(encoding="utf-8"))
    admin_only = [u for u in users if u.get("role") == "admin"]
    _write_json(users_path, admin_only)


def clear_master_db() -> dict[str, int]:
    init_db()
    counts: dict[str, int] = {}
    with SessionLocal() as db:
        for label, model in (
            ("shift_submissions", ShiftSubmission),
            ("legacy_assignments", Assignment),
            ("assignment_requests", AssignmentRequest),
            ("admin_overrides", AdminOverride),
            ("class_schedules", ClassSchedule),
            ("period_base_slots", PeriodBaseSlot),
            ("student_plans", StudentSubjectPlan),
            ("student_request_publishes", StudentScheduleRequestPublish),
            ("student_publishes", StudentSchedulePublish),
            ("teacher_publishes", TeacherSchedulePublish),
            ("teacher_request_publishes", TeacherScheduleRequestPublish),
            ("change_requests", ShiftChangeRequest),
            ("workbooks", PeriodScheduleWorkbook),
            ("teacher_slot_capacities", TeacherSlotCapacity),
            ("periods", Period),
            ("students", StudentProfile),
            ("teachers", TeacherProfile),
        ):
            counts[label] = db.query(model).delete()

        counts["app_settings"] = db.query(AppSetting).delete()

        for dash in db.query(ShiftDashboard).all():
            dash.teachers = []

        db.commit()

    return counts


def main() -> None:
    clear_master_json_files()
    counts = clear_master_db()
    print("講習・生徒・講師データを削除しました（教室長ログインのみ残しています）。")
    print(
        "  削除件数: "
        f"periods={counts['periods']}, "
        f"students={counts['students']}, "
        f"teachers={counts['teachers']}, "
        f"class_schedules={counts['class_schedules']}"
    )


if __name__ == "__main__":
    main()
