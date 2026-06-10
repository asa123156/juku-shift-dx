from schemas.assignment import AssignmentRecord, AutoAssignProposal
from services.assignment_engine import pick_best_candidate, teachers_from_dashboard
from services.assignment_grid import build_assignment_grid
from services.assignment_store import (
    add_assignment,
    clear_requests_fulfilled,
    get_assignment_requests_for_date,
    get_assignments_for_date,
)
from services.availability_dashboard import build_availability_dashboard


def run_auto_assign(date: str) -> tuple[list[AutoAssignProposal], list[AssignmentRecord], dict]:
    """未割当リクエストごとに候補を探索し、最適な講師×コマを割り当てる。"""
    dashboard = build_availability_dashboard(date)
    teacher_list = teachers_from_dashboard(dashboard)
    current_assignments = get_assignments_for_date(date)
    requests = get_assignment_requests_for_date(date)

    proposals: list[AutoAssignProposal] = []
    new_records: list[AssignmentRecord] = []
    fulfilled_ids: set[int] = set()

    for req in requests:
        student_id = req["student_id"]
        subject = req["subject"]

        best = pick_best_candidate(
            student_id=student_id,
            subject=subject,
            teacher_list=teacher_list,
            current_assignments=current_assignments,
            date=date,
        )
        if best is None:
            continue

        record = AssignmentRecord(
            date=date,
            student_id=student_id,
            student_name=req["student_name"],
            subject=subject,
            teacher_id=best["teacher_id"],
            teacher_name=best["teacher_name"],
            slot=best["slot"],
        )
        add_assignment(record)
        current_assignments.append(record.model_dump())
        fulfilled_ids.add(student_id)

        proposals.append(
            AutoAssignProposal(
                student_id=student_id,
                student_name=req["student_name"],
                subject=subject,
                teacher_id=best["teacher_id"],
                teacher_name=best["teacher_name"],
                slot=best["slot"],
                match_score=best["match_score"],
            )
        )
        new_records.append(record)

    if fulfilled_ids:
        clear_requests_fulfilled(date, fulfilled_ids)

    grid = build_assignment_grid(date)
    all_assignments = get_assignments_for_date(date)
    return proposals, [AssignmentRecord.model_validate(a) for a in all_assignments], grid
