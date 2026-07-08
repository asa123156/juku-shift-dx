import unittest

from fastapi import HTTPException

from services.student_slot_codec import (
    parse_student_slot,
    student_availability_label,
    validate_student_slot,
)


class StudentSlotCodecTests(unittest.TestCase):
    def test_parse_empty_and_unavailable(self) -> None:
        self.assertEqual(parse_student_slot("")["kind"], "空き")
        self.assertEqual(parse_student_slot("×")["kind"], "×")
        self.assertEqual(parse_student_slot("◎")["kind"], "通常授業")

    def test_validate_allows_empty_and_unavailable_only(self) -> None:
        self.assertEqual(validate_student_slot("×", {"数学"}), "×")
        self.assertEqual(validate_student_slot("", {"数学"}), "")
        with self.assertRaises(HTTPException):
            validate_student_slot("◎", set())

    def test_validate_rejects_legacy(self) -> None:
        with self.assertRaises(HTTPException):
            validate_student_slot("通常:理科", {"数学"})
        with self.assertRaises(HTTPException):
            validate_student_slot("講習:国語", set())

    def test_availability_label(self) -> None:
        self.assertEqual(student_availability_label("通常:数学"), "空き（旧:数学）")
        self.assertEqual(student_availability_label("×"), "×")
        self.assertEqual(student_availability_label(""), "空き")
        self.assertEqual(student_availability_label("◎"), "通常授業")


if __name__ == "__main__":
    unittest.main()
