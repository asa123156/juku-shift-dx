"""デモデータを生成して DB に再投入する。

Usage:
    cd backend && python -m scripts.reset_demo
"""

from database import SessionLocal, init_db
from models import ShiftSubmission
from services.assignment_store import reset_assignments_from_json
from services.dashboard_store import reset_shift_dashboards_for_tests
from services.period_store import reset_periods_for_tests
from services.submission_store import reset_submissions_for_tests


def reset_submissions_from_json() -> int:
    from config import DATA_DIR
    import json
    from datetime import date

    from services.slot_timing import SLOT_KEYS

    reset_submissions_for_tests()
    count = 0
    with SessionLocal() as db:
        for path, role in (
            (DATA_DIR / "teacher-submissions.json", "teacher"),
            (DATA_DIR / "student-submissions.json", "student"),
        ):
            if not path.is_file():
                continue
            raw = json.loads(path.read_text(encoding="utf-8"))
            for iso_date, entities in raw.items():
                if not isinstance(entities, dict):
                    continue
                slot_date = date.fromisoformat(iso_date)
                for entity_key, slots in entities.items():
                    if not entity_key.isdigit() or not isinstance(slots, dict):
                        continue
                    entity_id = int(entity_key)
                    for slot_key, symbol in slots.items():
                        if slot_key not in SLOT_KEYS:
                            continue
                        db.add(
                            ShiftSubmission(
                                role=role,
                                entity_id=entity_id,
                                slot_date=slot_date,
                                slot_key=slot_key,
                                symbol=symbol,
                            )
                        )
                        count += 1
        db.commit()
    return count


def main() -> None:
    from scripts.generate_demo_data import main as generate

    generate()
    init_db()
    reset_periods_for_tests()
    from services.entity_store import reset_entities_for_tests

    reset_entities_for_tests()
    reset_shift_dashboards_for_tests()
    sub_count = reset_submissions_from_json()
    assign_count, request_count = reset_assignments_from_json()
    print(f"再投入完了: 提出 {sub_count} 件 / 割当 {assign_count} 件 / リクエスト {request_count} 件")
    print("管理画面 → 生徒割当 → 生徒を選んでスケジュールを確認")


if __name__ == "__main__":
    main()
