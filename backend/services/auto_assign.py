from schemas.assignment import AssignmentRecord, AutoAssignProposal
from services.assignment_engine import pick_best_candidate, teachers_from_dashboard
from services.assignment_grid import build_assignment_grid
from services.match_rules import MatchRules
from services.assignment_store import add_assignment, get_assignments_for_date
from services.period_store import find_period_for_date
from services.schedule_canonical import derive_unassigned_for_date
from services.availability_dashboard import build_availability_dashboard
from services.student_plan_store import get_preferred_teacher_id


def run_auto_assign(
    date: str,
    rules: MatchRules | None = None,
    all_assignments: list[dict] | None = None,
) -> tuple[list[AutoAssignProposal], list[AssignmentRecord], dict]:
    """未割当リクエストごとに候補を探索し、最適な講師×コマを割り当てる。"""
    rules = rules or MatchRules()
    dashboard = build_availability_dashboard(date)
    teacher_list = teachers_from_dashboard(dashboard)
    current_assignments = get_assignments_for_date(date)
    pool = all_assignments if all_assignments is not None else list(current_assignments)
    period = find_period_for_date(date)
    if period is not None:
        requests = derive_unassigned_for_date(period.id, date)
    else:
        requests = []

    proposals: list[AutoAssignProposal] = []
    new_records: list[AssignmentRecord] = []

    for req in requests:
        student_id = req["student_id"]
        subject = req["subject"]

        preferred = (
            get_preferred_teacher_id(period.id, student_id, subject) if period is not None else None
        )

        best = pick_best_candidate(
            student_id=student_id,
            subject=subject,
            teacher_list=teacher_list,
            current_assignments=current_assignments,
            date=date,
            rules=rules,
            all_assignments=pool,
            preferred_teacher_id=preferred,
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
        dumped = record.model_dump()
        current_assignments.append(dumped)
        if all_assignments is not None:
            pool.append(dumped)

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

    grid = build_assignment_grid(date)
    all_assignments_day = get_assignments_for_date(date)
    return proposals, [AssignmentRecord.model_validate(a) for a in all_assignments_day], grid
