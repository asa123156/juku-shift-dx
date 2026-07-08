from typing import Literal

from pydantic import BaseModel, Field

from schemas.period import SubmitRole
from services.slot_timing import SLOT_COUNT

ChangeRequestStatus = Literal["PENDING", "APPROVED", "REJECTED"]


class ChangeRequestItem(BaseModel):
    id: int
    period_id: int
    role: SubmitRole
    entity_id: int
    entity_name: str
    date: str
    slot: int
    current_symbol: str
    requested_symbol: str
    reason: str = ""
    status: ChangeRequestStatus
    request_type: str = "SLOT"


class ResubmitRequestCreateRequest(BaseModel):
    period_id: int = Field(ge=1)
    role: SubmitRole
    entity_id: int = Field(ge=1)
    reason: str = Field(default="", max_length=500)


class ResubmitRequestCreateResponse(BaseModel):
    request: ChangeRequestItem
    message: str


class ChangeRequestCreateRequest(BaseModel):
    period_id: int = Field(ge=1)
    role: SubmitRole
    entity_id: int = Field(ge=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    slot: int = Field(ge=1, le=SLOT_COUNT)
    requested_symbol: str = Field(description="希望する状態")
    reason: str = Field(default="", max_length=500)


class ChangeRequestCreateResponse(BaseModel):
    request: ChangeRequestItem
    message: str


class ChangeRequestListResponse(BaseModel):
    period_id: int
    requests: list[ChangeRequestItem]
    pending_count: int = 0


class ChangeRequestResolveRequest(BaseModel):
    action: Literal["approve", "reject"]


class ChangeRequestResolveResponse(BaseModel):
    request: ChangeRequestItem
    message: str


class PublishAllRequest(BaseModel):
    period_id: int = Field(ge=1)


class PublishAllResponse(BaseModel):
    period_id: int
    students_published: int
    students_skipped: list[str] = Field(default_factory=list, description="未割当が残りスキップした生徒名")
    teachers_published: int
    message: str
