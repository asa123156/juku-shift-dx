"""スケジュール中身だけを空にする（期間・生徒・講師マスタは残す）。

Usage:
    cd backend && python -m scripts.clear_schedules
"""

from __future__ import annotations

import json
from pathlib import Path

from config import DATA_DIR
from database import SessionLocal, init_db
from models import (
    AdminOverride,
    Assignment,
    AssignmentRequest,
    ClassSchedule,
    PeriodBaseSlot,
    PeriodScheduleWorkbook,
    ShiftChangeRequest,
    ShiftSubmission,
    StudentSchedulePublish,
    StudentScheduleRequestPublish,
    StudentSubjectPlan,
    TeacherSchedulePublish,
    TeacherScheduleRequestPublish,
)
from services.admin_store import reset_admin_overrides_for_tests
from services.assignment_store import reset_assignments_for_tests
from services.submission_store import reset_submissions_for_tests


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clear_schedule_json_files() -> None:
    _write_json(DATA_DIR / "student-submissions.json", {})
    _write_json(DATA_DIR / "teacher-submissions.json", {})
    _write_json(DATA_DIR / "assignments.json", {})
    _write_json(DATA_DIR / "assignment-requests.json", {})
    _write_json(DATA_DIR / "period-bases.json", {})


def clear_schedule_db() -> dict[str, int]:
    init_db()
    reset_submissions_for_tests()
    reset_assignments_for_tests()
    reset_admin_overrides_for_tests()

    counts: dict[str, int] = {}
    with SessionLocal() as db:
        counts["legacy_assignments"] = db.query(Assignment).delete()
        counts["class_schedules"] = db.query(ClassSchedule).delete()
        for label, model in (
            ("period_base_slots", PeriodBaseSlot),
            ("student_plans", StudentSubjectPlan),
            ("student_request_publishes", StudentScheduleRequestPublish),
            ("student_publishes", StudentSchedulePublish),
            ("teacher_publishes", TeacherSchedulePublish),
            ("teacher_request_publishes", TeacherScheduleRequestPublish),
            ("change_requests", ShiftChangeRequest),
            ("workbooks", PeriodScheduleWorkbook),
        ):
            counts[label] = db.query(model).delete()
        db.commit()

    with SessionLocal() as db:
        counts["shift_submissions"] = db.query(ShiftSubmission).count()
        counts["class_schedules_left"] = db.query(ClassSchedule).count()
        counts["assignment_requests"] = db.query(AssignmentRequest).count()
        counts["admin_overrides"] = db.query(AdminOverride).count()
        counts["legacy_assignments_left"] = db.query(Assignment).count()

    return counts


def main() -> None:
    clear_schedule_json_files()
    counts = clear_schedule_db()
    print("スケジュールを空にしました（期間・生徒・講師マスタはそのまま）。")
    print(f"  DB 残件: submissions={counts['shift_submissions']}, "
          f"class_schedules={counts['class_schedules_left']}, requests={counts['assignment_requests']}")
    print(f"  削除: period_base={counts['period_base_slots']}, "
          f"publishes={counts['student_publishes']}+{counts['teacher_publishes']}, "
          f"workbooks={counts['workbooks']}")


if __name__ == "__main__":
    main()
