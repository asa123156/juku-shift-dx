"""生徒スケジュール提出の記号エンコード（通常:科目 / 講習:科目 / ×）。"""

from __future__ import annotations

from fastapi import HTTPException

PREFIX_REGULAR = "通常:"
PREFIX_CRAM = "講習:"


def parse_student_slot(value: str) -> dict[str, str]:
    if value == "◎":
        return {"kind": "◎", "subject": ""}
    if value == "×":
        return {"kind": "×", "subject": ""}
    if not value:
        return {"kind": "", "subject": ""}
    if value.startswith(PREFIX_REGULAR):
        return {"kind": "通常", "subject": value[len(PREFIX_REGULAR) :].strip()}
    if value.startswith(PREFIX_CRAM):
        return {"kind": "講習", "subject": value[len(PREFIX_CRAM) :].strip()}
    return {"kind": "?", "subject": value}


def encode_student_slot(kind: str, subject: str = "") -> str:
    if kind == "×":
        return "×"
    sub = subject.strip()
    if kind == "通常":
        if not sub:
            raise ValueError("通常を選ぶ場合は教科を指定してください")
        return f"{PREFIX_REGULAR}{sub}"
    if kind == "講習":
        if not sub:
            raise ValueError("講習を選ぶ場合は教科を指定してください")
        return f"{PREFIX_CRAM}{sub}"
    return ""


def validate_student_slot(value: str, allowed_subjects: set[str] | None = None) -> str:
    if value == "◎":
        raise HTTPException(status_code=400, detail="生徒は ◎ を設定できません")
    if value == "":
        return ""
    if value == "×":
        return "×"
    parsed = parse_student_slot(value)
    if parsed["kind"] not in ("通常", "講習"):
        raise HTTPException(status_code=400, detail=f"無効な提出値です: {value}")
    if not parsed["subject"]:
        raise HTTPException(status_code=400, detail="教科名が必要です")
    if len(parsed["subject"]) > 32:
        raise HTTPException(status_code=400, detail="教科名が長すぎます")
    if allowed_subjects and parsed["subject"] not in allowed_subjects:
        raise HTTPException(
            status_code=400,
            detail=f"教科 {parsed['subject']} は希望設定にありません",
        )
    return encode_student_slot(parsed["kind"], parsed["subject"])


def is_valid_student_change_symbol(value: str, allowed_subjects: set[str] | None = None) -> bool:
    if value == "":
        return True
    try:
        validate_student_slot(value, allowed_subjects)
        return True
    except HTTPException:
        return False


def subjects_match_for_assignment(assignment_subject: str, slot_subject: str) -> bool:
    from services.match_rules import normalize_limit_subject

    a = normalize_limit_subject(assignment_subject.strip())
    b = normalize_limit_subject(slot_subject.strip())
    if a == b:
        return True
    return assignment_subject.strip() == slot_subject.strip()


def is_student_slot_assignable(symbol: str, subject: str) -> bool:
    """生徒提出記号が、指定科目の割当を許可するか。"""
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "×":
        return False
    if parsed["kind"] == "◎":
        return False
    if parsed["kind"] in ("通常", "講習"):
        if not parsed["subject"]:
            return False
        return subjects_match_for_assignment(subject, parsed["subject"])
    return True


def student_slot_block_reason(symbol: str, subject: str) -> str | None:
    if is_student_slot_assignable(symbol, subject):
        return None
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "×":
        return "生徒がこのコマを不可（×）にしています"
    if parsed["kind"] in ("通常", "講習"):
        return f"生徒の希望（{symbol}）と科目 {subject} が一致しません"
    return "生徒の提出内容によりこのコマには割当できません"


def student_slot_preference_bonus(symbol: str, subject: str) -> int:
    parsed = parse_student_slot(symbol)
    if parsed["kind"] in ("通常", "講習") and parsed["subject"]:
        if subjects_match_for_assignment(subject, parsed["subject"]):
            return 15
    return 0


def student_availability_label(symbol: str) -> str:
    parsed = parse_student_slot(symbol)
    if parsed["kind"] == "◎":
        return "◎"
    if parsed["kind"] == "×":
        return "×"
    if parsed["kind"] == "通常":
        return f"通常:{parsed['subject']}" if parsed["subject"] else "通常"
    if parsed["kind"] == "講習":
        return f"講習:{parsed['subject']}" if parsed["subject"] else "講習"
    return "空き"
