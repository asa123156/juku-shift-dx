from pydantic import BaseModel, Field


class StudentLesson(BaseModel):
    student_name: str
    subject_name: str


class LessonRow(BaseModel):
    date: str = Field(description="ISO日付 YYYY-MM-DD")
    time_slot: int = Field(ge=1)
    teacher_name: str
    students: list[StudentLesson]
