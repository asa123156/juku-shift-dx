from pydantic import BaseModel, Field, field_validator

SchoolLevel = str  # elementary | middle | high


class StudentProfile(BaseModel):
    id: int
    name: str
    school_level: str
    grade_year: int
    grade_label: str
    level_label: str
    login_id: str = ""
    password: str = ""


class StudentCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    school_level: str = Field(description="elementary | middle | high")
    grade_year: int = Field(ge=1, le=6)


class StudentUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    school_level: str = Field(description="elementary | middle | high")
    grade_year: int = Field(ge=1, le=6)


class StudentListResponse(BaseModel):
    students: list[StudentProfile]


class StudentGroup(BaseModel):
    school_level: str
    level_label: str
    grade_year: int
    grade_label: str
    students: list[StudentProfile]


class StudentGroupedResponse(BaseModel):
    groups: list[StudentGroup]


class TeacherProfile(BaseModel):
    id: int
    name: str
    color: str = ""
    login_id: str = ""
    password: str = ""


class TeacherCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    color: str | None = None


class TeacherUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    color: str | None = None


class TeacherListResponse(BaseModel):
    teachers: list[TeacherProfile]


class PeriodActivateRequest(BaseModel):
    period_id: int = Field(ge=1)
