"""Versioned event coverage contract for HTTP operations.

The matrix is intentionally explicit: adding a mutating or sensitive-read API
without declaring its evidence must fail a test before release.
"""

from dataclasses import dataclass
from typing import Literal

EventLayer = Literal["audit", "security", "audit+security"]


@dataclass(frozen=True, slots=True)
class EventCoverage:
    layer: EventLayer
    event: str


MUTATION_EVENT_COVERAGE: dict[str, EventCoverage] = {
    "auth_login": EventCoverage("security", "login_succeeded|login_failed"),
    "auth_logout": EventCoverage("security", "logout_succeeded"),
    "auth_revoke_company_session": EventCoverage("audit+security", "session.revoke"),
    "auth_revoke_membership_sessions": EventCoverage(
        "audit+security", "session.revoke_all"
    ),
    "case_create": EventCoverage("audit", "case.create"),
    "case_from_quotation": EventCoverage("audit", "quotation.convert_to_case"),
    "case_update": EventCoverage("audit", "case.update"),
    "case_void": EventCoverage("audit", "case.void"),
    "customer_create": EventCoverage("audit", "customer.create"),
    "customer_update": EventCoverage("audit", "customer.update"),
    "customer_status_update": EventCoverage("audit", "customer.status_update"),
    "customer_work_item_create": EventCoverage("audit", "customer_work_item.create"),
    "customer_work_item_update": EventCoverage("audit", "customer_work_item.update"),
    "customer_work_item_status_update": EventCoverage(
        "audit", "customer_work_item.status_update"
    ),
    "document_pdf_export_create": EventCoverage("audit", "document.pdf_export"),
    "inventory_adjustment_create": EventCoverage("audit", "inventory.adjust"),
    "organization_profile_update": EventCoverage("audit", "organization.profile_update"),
    "organization_settings_update": EventCoverage(
        "audit", "organization.settings_update"
    ),
    "paper_mill_create": EventCoverage("audit", "paper_mill.create"),
    "paper_mill_update": EventCoverage("audit", "paper_mill.update"),
    "paper_mill_status_update": EventCoverage("audit", "paper_mill.status_update"),
    "paper_type_create": EventCoverage("audit", "paper_type.create"),
    "paper_type_update": EventCoverage("audit", "paper_type.update"),
    "paper_type_status_update": EventCoverage("audit", "paper_type.status_update"),
    "pricing_cancel": EventCoverage("audit", "pricing.cancel"),
    "pricing_confirm": EventCoverage("audit", "pricing.confirm"),
    "pricing_create": EventCoverage("audit", "pricing.create"),
    "pricing_reopen": EventCoverage("audit", "pricing.reopen"),
    "pricing_update": EventCoverage("audit", "pricing.update"),
    "process_definition_status_update": EventCoverage(
        "audit", "process_definition.status_update"
    ),
    "production_final_completion_create": EventCoverage(
        "audit", "production.final_completion"
    ),
    "production_final_completion_reverse": EventCoverage(
        "audit", "production.final_completion_reverse"
    ),
    "production_process_event_create": EventCoverage(
        "audit", "production.process_event"
    ),
    "quotation_clone": EventCoverage("audit", "quotation.create"),
    "quotation_confirm": EventCoverage("audit", "quotation.confirm"),
    "quotation_create": EventCoverage("audit", "quotation.create"),
    "quotation_update": EventCoverage("audit", "quotation.update"),
    "quotation_void": EventCoverage("audit", "quotation.void"),
    "receipt_create": EventCoverage("audit", "receipt.record"),
    "receipt_reverse": EventCoverage("audit", "receipt.reverse"),
    "shipment_cancel": EventCoverage("audit", "shipment.cancel"),
    "shipment_confirm": EventCoverage("audit", "shipment.confirm"),
    "shipment_create": EventCoverage("audit", "shipment.create"),
    "shipment_update": EventCoverage("audit", "shipment.update"),
    "statement_cancel": EventCoverage("audit", "statement.cancel"),
    "statement_create": EventCoverage("audit", "statement.create"),
    "statement_issue": EventCoverage("audit", "statement.issue"),
    "vendor_create": EventCoverage("audit", "vendor.create"),
    "vendor_status_update": EventCoverage("audit", "vendor.status_update"),
    "vendor_update": EventCoverage("audit", "vendor.update"),
    "work_order_attachment_delete": EventCoverage(
        "audit", "work_order.attachment.delete"
    ),
    "work_order_attachment_upload": EventCoverage(
        "audit", "work_order.attachment.upload"
    ),
    "work_order_clone": EventCoverage("audit", "work_order.clone"),
    "work_order_confirm": EventCoverage("audit", "work_order.confirm"),
    "work_order_create": EventCoverage("audit", "work_order.create"),
    "work_order_update": EventCoverage("audit", "work_order.update"),
    "work_order_void": EventCoverage("audit", "work_order.void"),
}


SENSITIVE_READ_EVENT_COVERAGE: dict[str, EventCoverage] = {
    "audit_list": EventCoverage("audit", "audit.read"),
    "auth_list_company_sessions": EventCoverage("audit", "session.list_company"),
    "document_pdf_export_download": EventCoverage("audit", "document.pdf_download"),
    "operations_export_csv": EventCoverage("audit", "operations.csv_export"),
    "work_order_attachment_download": EventCoverage(
        "audit", "work_order.attachment.download"
    ),
}
