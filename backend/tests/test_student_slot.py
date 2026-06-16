import unittest

from fastapi import HTTPException

from services.student_slot_codec import (
    encode_student_slot,
    parse_student_slot,
    student_availability_label,
    validate_student_slot,
)


class StudentSlotCodecTests(unittest.TestCase):
    def test_encode_parse_roundtrip(self) -> None:
        for kind, subject in [("通常", "数学"), ("講習", "英語")]:
            encoded = encode_student_slot(kind, subject)
            parsed = parse_student_slot(encoded)
            self.assertEqual(parsed["kind"], kind)
            self.assertEqual(parsed["subject"], subject)

    def test_validate_unavailable(self) -> None:
        self.assertEqual(validate_student_slot("×", {"数学"}), "×")
        self.assertEqual(validate_student_slot("", {"数学"}), "")

    def test_validate_requires_plan_subject_when_configured(self) -> None:
        with self.assertRaises(HTTPException):
            validate_student_slot("通常:理科", {"数学"})
        self.assertEqual(validate_student_slot("通常:数学", {"数学"}), "通常:数学")

    def test_validate_allows_any_subject_when_no_plans(self) -> None:
        self.assertEqual(validate_student_slot("講習:国語", set()), "講習:国語")

    def test_availability_label(self) -> None:
        self.assertEqual(student_availability_label("通常:数学"), "通常:数学")
        self.assertEqual(student_availability_label("×"), "×")


if __name__ == "__main__":
    unittest.main()
