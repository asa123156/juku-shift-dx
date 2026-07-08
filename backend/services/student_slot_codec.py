"""生徒スケジュール提出: 空き（""）/ × のみ。通常授業は時間割表（is_fixed）で管理。"""

from __future__ import annotations

from fastapi import HTTPException


def parse_student_slot(value: str) -> dict[str, str]:
    if value == "×":
        return {"kind": "×", "subject": ""}
    if not value or value == "◎":
        # ◎ は旧データ互換: 表示上は通常授業（時間割表参照）
        return {"kind": "通常授業" if value == "◎" else "空き", "subject": ""}
    if value.startswith(("通常:", "講習:")):
        return {"kind": "legacy", "subject": value[3:].strip()}
    return {"kind": "?", "subject": value}


def validate_student_slot(value: str, allowed_subjects: set[str] | None = None) -> str:
    del allowed_subjects
    if value in ("", "×"):
        return value
    if value == "◎":
        raise HTTPException(
            status_code=400,
            detail="通常授業は時間割表で管理されています。空きまたは × のみ提出できます",
        )
    raise HTTPException(status_code=400, detail="生徒は 空き・× のみ提出できます")


def is_valid_student_change_symbol(value: str, allowed_subjects: set[str] | None = None) -> bool:
    try:
        validate_student_slot(value, allowed_subjects)
        return True
    except HTTPException:
        return False


def is_student_slot_assignable(symbol: str, subject: str) -> bool:
    del subject
    parsed = parse_student_slot(symbol)
    if parsed["kind"] in ("×", "通常授業"):
        return False
    return True


def student_slot_block_reason(symbol: str, subject: str) -> str | None:
    if is_student_slot_assignable(symbol, subject):
        return None
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "×":
        return "生徒がこのコマを不可（×）にしています"
    if parsed["kind"] == "通常授業":
        return "通常授業のコマです"
    return "このコマには割当できません"


def student_availability_label(symbol: str) -> str:
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "通常授業":
        return "通常授業"
    if parsed["kind"] == "×":
        return "×"
    if parsed["kind"] == "空き":
        return "空き"
    if parsed["kind"] == "legacy":
        return f"空き（旧:{parsed['subject']}）" if parsed["subject"] else "空き"
    return "空き"
