"""Fast PDF renderer contract tests without a database."""

from base64 import b64decode

from reportlab.pdfbase.pdfdoc import PDFCatalog

from app.modules.document_exports.renderer import render_document_pdf

COMPANY = {"name": "虛構印刷公司", "address": "測試地址", "phone": "02-0000-0000"}
ONE_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _assert_pdf(kind: str, data: dict) -> None:
    output = render_document_pdf(kind, data, COMPANY)
    assert output.startswith(b"%PDF-")
    assert output.endswith(b"%%EOF\n")
    assert 1_000 < len(output) < 5_000_000


def test_renders_all_supported_document_templates() -> None:
    _assert_pdf(
        "quotation",
        {
            "document_number": "QUO-20260813-01",
            "quotation_date": "2026-08-13",
            "customer_snapshot": {"code": "C001", "name": "虛構客戶"},
            "items": [
                {
                    "line_number": 1,
                    "product_name": "彩盒",
                    "size": "10x20",
                    "paper": "白卡",
                    "color": "四色",
                    "coating": "亮膜",
                    "plate_fee": "100",
                    "die_fee": "200",
                    "quantity": "1000",
                    "unit_price": "10",
                    "note": "測試",
                }
            ],
        },
    )
    _assert_pdf(
        "work_order",
        {
            "document_number": "WO-20260813-001",
            "customer_snapshot": {"code": "C001", "name": "虛構客戶"},
            "product_name": "彩盒",
            "order_quantity": "1000",
            "papers": [],
            "print_specification": {"front": {"c": True}, "back": {}},
            "processes": [{"code": "printing", "name": "印刷", "content": "四色"}],
            "print_attachments": [
                {
                    "filename": "盒型示意.png",
                    "mime_type": "image/png",
                    "content": ONE_PIXEL_PNG,
                }
            ],
        },
    )
    _assert_pdf(
        "shipment",
        {
            "document_number": "SHP-202608-001",
            "shipment_date": "2026-08-13",
            "customer_name": "虛構客戶",
            "items": [],
        },
    )
    _assert_pdf(
        "statement",
        {
            "document_number": "STM-202608-001",
            "statement_date": "2026-08-13",
            "customer_name": "虛構客戶",
            "period_from": "2026-08-01",
            "period_to": "2026-08-31",
            "items": [],
            "subtotal_before_rounding": "1000",
            "rounding_adjustment": "0",
            "tax_amount": "0",
            "grand_total": "1000",
            "tax_enabled": False,
        },
    )


def test_reportlab_is_available_as_runtime_dependency() -> None:
    assert PDFCatalog is not None
