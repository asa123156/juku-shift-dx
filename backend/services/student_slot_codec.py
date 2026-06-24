"""生徒スケジュール提出: 空き（""）/ × のみ。◎ は教室長が period_base で設定。"""

from __future__ import annotations

from fastapi import HTTPException


def parse_student_slot(value: str) -> dict[str, str]:
    if value == "◎":
        return {"kind": "◎", "subject": ""}
    if value == "×":
        return {"kind": "×", "subject": ""}
    if not value:
        return {"kind": "空き", "subject": ""}
    # 旧形式（通常:科目 / 講習:科目）は読取のみ
    if value.startswith("通常:"):
        return {"kind": "legacy", "subject": value[3:].strip()}
    if value.startswith("講習:"):
        return {"kind": "legacy", "subject": value[3:].strip()}
    return {"kind": "?", "subject": value}


def validate_student_slot(value: str, allowed_subjects: set[str] | None = None) -> str:
    del allowed_subjects  # 生徒提出に教科選択はない
    if value == "◎":
        raise HTTPException(status_code=400, detail="生徒は ◎ を設定できません")
    if value == "":
        return ""
    if value == "×":
        return "×"
    if value.startswith("通常:") or value.startswith("講習:"):
        raise HTTPException(
            status_code=400,
            detail="生徒は 空き または × のみ提出できます",
        )
    raise HTTPException(status_code=400, detail=f"無効な提出値です: {value}")


def is_valid_student_change_symbol(value: str, allowed_subjects: set[str] | None = None) -> bool:
    if value in ("", "×"):
        return True
    try:
        validate_student_slot(value, allowed_subjects)
        return True
    except HTTPException:
        return False


def is_student_slot_assignable(symbol: str, subject: str) -> bool:
    """割当可否: × のみ不可。空きコマは科目問わず可。"""
    del subject
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "×":
        return False
    if parsed["kind"] == "◎":
        return False
    return True


def student_slot_block_reason(symbol: str, subject: str) -> str | None:
    if is_student_slot_assignable(symbol, subject):
        return None
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "×":
        return "生徒がこのコマを不可（×）にしています"
    return "このコマには割当できません"


def student_availability_label(symbol: str) -> str:
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "◎":
        return "◎"
    if parsed["kind"] == "×":
        return "×"
    if parsed["kind"] == "空き":
        return "空き"
    if parsed["kind"] == "legacy":
        return f"空き（旧:{parsed['subject']}）" if parsed["subject"] else "空き"
    return "空き"
