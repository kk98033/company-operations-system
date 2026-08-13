"""Typed contracts for cases, work orders, conversion, and attachments."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.contracts import ListResponse, SortDirection, SortParams

PROCESS_CODES = (
    "artwork",
    "output",
    "plate",
    "proof",
    "printing",
    "coating",
    "mounting",
    "die",
    "die_cutting",
    "finishing",
    "gluing",
    "transport",
    "other",
)
PROCESS_NAMES = (
    "美工",
    "輸出",
    "製版",
    "打樣",
    "印刷",
    "上光",
    "裱紙",
    "模具",
    "軋型",
    "加工",
    "糊邊",
    "運送",
    "其他",
)
PRINT_PROCESS_CODES = (
    "plate",
    "proof",
    "printing",
    "coating",
    "mounting",
    "die_cutting",
    "finishing",
    "gluing",
    "other",
)


class CaseStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    VOID = "void"


class WorkOrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    VOID = "void"


class PaperMaterial(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    type: str = Field(pattern="^(face|back|flute)$")
    vendor: str | None = Field(default=None, max_length=200)
    paper: str | None = Field(default=None, max_length=200)
    mill: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=100)
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_type_contract(self) -> "PaperMaterial":
        if self.type == "flute" and self.mill:
            raise ValueError("浪紙新建檔不可填廠別")
        return self


class PrintSide(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color_count: int | None = Field(default=None, ge=0, le=20)
    c: bool = False
    m: bool = False
    y: bool = False
    k: bool = False
    special_colors: str | None = Field(default=None, max_length=2000)


class PrintSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    length: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    width: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    k_count: int | None = Field(default=None, ge=0)
    imposition_count: int | None = Field(default=None, ge=0)
    print_quantity: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)
    variance: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    front: PrintSide = Field(default_factory=PrintSide)
    back: PrintSide = Field(default_factory=PrintSide)
    total_color_count: int | None = Field(default=None, ge=0, le=40)


class ProcessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str
    name: str
    vendor: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=2000)
    plate_version: str | None = Field(default=None, pattern="^(new|existing)$")
    plate_rotation: str | None = Field(default=None, pattern="^(top_bottom|left_right)$")
    coating_type: str | None = Field(default=None, max_length=200)
    die_number: str | None = Field(default=None, max_length=100)
    die_count: int | None = Field(default=None, ge=0)
    packing: str | None = Field(default=None, pattern="^(box|bag)$")

    @model_validator(mode="after")
    def validate_process_specific_fields(self) -> "ProcessPlan":
        if self.code != "plate" and (self.plate_version or self.plate_rotation):
            raise ValueError("製版選項只能填在製版製程")
        if self.code != "coating" and self.coating_type:
            raise ValueError("上光種類只能填在上光製程")
        if self.code != "die_cutting" and (self.die_number or self.die_count is not None):
            raise ValueError("刀模資料只能填在軋型製程")
        if self.code != "gluing" and self.packing:
            raise ValueError("裝箱／裝袋只能填在糊邊製程")
        return self


class WorkOrderWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    order_date: date
    delivery_date: date | None = None
    customer_id: UUID
    customer_order_number: str | None = Field(default=None, max_length=100)
    product_name: str = Field(min_length=1, max_length=500)
    order_quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    specification: str | None = Field(default=None, max_length=4000)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    plate_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    die_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    papers: list[PaperMaterial]
    print_specification: PrintSpecification = Field(default_factory=PrintSpecification)
    processes: list[ProcessPlan]
    notes: str | None = Field(default=None, max_length=12000)

    @model_validator(mode="after")
    def validate_company_form(self) -> "WorkOrderWrite":
        if tuple(item.type for item in self.papers) != ("face", "back", "flute"):
            raise ValueError("備紙必須依序包含面紙、底紙、浪紙")
        if tuple(item.code for item in self.processes) != PROCESS_CODES:
            raise ValueError("製程必須依公司稿固定 13 道順序")
        if tuple(item.name for item in self.processes) != PROCESS_NAMES:
            raise ValueError("製程名稱與公司稿不一致")
        return self


class WorkOrderCreate(WorkOrderWrite):
    case_id: UUID | None = None


class WorkOrderUpdate(WorkOrderWrite):
    expected_updated_at: datetime


class VersionRequest(BaseModel):
    expected_updated_at: datetime


class VoidRequest(VersionRequest):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=1, max_length=1000)


class WorkOrderResponse(WorkOrderWrite):
    id: UUID
    case_id: UUID
    document_number: str
    status: WorkOrderStatus
    organization_snapshot: dict
    customer_snapshot: dict
    source_quotation_item_id: UUID | None
    source_work_order_id: UUID | None
    legacy_document_number: str | None
    document_snapshot: dict | None
    print_metadata: dict | None
    confirmed_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None
    created_at: datetime
    updated_at: datetime


class WorkOrderSummary(BaseModel):
    id: UUID
    case_id: UUID
    document_number: str
    legacy_document_number: str | None
    order_date: date
    delivery_date: date | None
    customer_order_number: str | None
    customer_name: str
    product_name: str
    order_quantity: Decimal
    unit_price: Decimal
    plate_fee: Decimal
    die_fee: Decimal
    status: WorkOrderStatus


class WorkOrderFilters(BaseModel):
    keyword: str | None
    status: WorkOrderStatus | None


class WorkOrderListResponse(ListResponse[WorkOrderSummary, WorkOrderFilters]):
    pass


class CaseResponse(BaseModel):
    id: UUID
    case_number: str
    case_date: date
    customer_id: UUID
    customer_snapshot: dict
    status: CaseStatus
    notes: str | None
    source_quotation_id: UUID | None
    legacy_document_number: str | None
    voided_at: datetime | None
    void_reason: str | None
    created_at: datetime
    updated_at: datetime
    work_orders: list[WorkOrderSummary]


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    case_date: date
    customer_id: UUID
    notes: str | None = Field(default=None, max_length=4000)


class CaseUpdate(CaseCreate):
    expected_updated_at: datetime


class CaseSummary(BaseModel):
    id: UUID
    case_number: str
    case_date: date
    customer_name: str
    status: CaseStatus
    work_order_count: int
    confirmed_count: int
    updated_at: datetime


class CaseFilters(BaseModel):
    keyword: str | None
    status: CaseStatus | None


class CaseListResponse(ListResponse[CaseSummary, CaseFilters]):
    pass


class CaseSortField(StrEnum):
    DATE = "case_date"


class CaseSortParams(SortParams[CaseSortField]):
    sort_by: CaseSortField = CaseSortField.DATE
    sort_direction: SortDirection = SortDirection.DESC


class WorkOrderSortField(StrEnum):
    DATE = "order_date"


class WorkOrderSortParams(SortParams[WorkOrderSortField]):
    sort_by: WorkOrderSortField = WorkOrderSortField.DATE
    sort_direction: SortDirection = SortDirection.DESC


class QuotationConversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quotation_id: UUID
    item_ids: list[UUID] = Field(min_length=1, max_length=50)


class AttachmentResponse(BaseModel):
    id: UUID
    work_order_id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at: datetime

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, value: str) -> str:
        return value
