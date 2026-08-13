"""Document export API contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

DocumentType = Literal["quotation", "work_order", "shipment", "statement"]


class DocumentExportResponse(BaseModel):
    id: UUID
    document_type: DocumentType
    document_id: UUID
    document_number: str
    document_version: str
    template_version: str
    filename: str
    content_type: Literal["application/pdf"]
    byte_size: int
    sha256: str
    download_url: str
    created_at: datetime
