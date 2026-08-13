"""Deterministic A4 PDF builders for supported business documents."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FONT = "NotoSansTC"
FONT_PATH = Path(__file__).with_name("assets") / "NotoSansTC.ttf"
pdfmetrics.registerFont(TTFont(FONT, FONT_PATH))

_styles = getSampleStyleSheet()
BODY = ParagraphStyle("CjkBody", parent=_styles["BodyText"], fontName=FONT, fontSize=8.5, leading=12)
SMALL = ParagraphStyle("CjkSmall", parent=BODY, fontSize=7.2, leading=9)
TITLE = ParagraphStyle(
    "CjkTitle", parent=BODY, fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=5 * mm
)
COMPANY = ParagraphStyle("CjkCompany", parent=BODY, fontSize=14, leading=18)
RIGHT = ParagraphStyle("CjkRight", parent=BODY, alignment=TA_RIGHT)


def _text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def _p(value: Any, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(escape(_text(value)).replace("\n", "<br/>"), style)


def _table(rows: list[list[Any]], widths: list[float], *, header: bool = False) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#56606b")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe5ea")),
                ("FONTNAME", (0, 0), (-1, 0), FONT),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def _company_header(company: dict[str, Any], title: str, *, wide: bool = False) -> list[Any]:
    contact = " | ".join(
        value for value in [_text(company.get("phone")), _text(company.get("fax")), _text(company.get("email"))] if value != "-"
    )
    return [
        Table(
            [[_p(company.get("name"), COMPANY), _p(title, TITLE)]],
            colWidths=[180 * mm, 87 * mm] if wide else [115 * mm, 55 * mm],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
        ),
        _p(company.get("address")),
        _p(contact),
        Spacer(1, 4 * mm),
    ]


def _quotation_story(data: dict[str, Any], company: dict[str, Any]) -> list[Any]:
    customer = data.get("customer_snapshot") or {}
    story = _company_header(company, "報 價 單", wide=True)
    story.append(
        _table(
            [
                [_p("客戶"), _p(f"{_text(customer.get('code'))} {_text(customer.get('name'))}"), _p("報價號碼"), _p(data.get("document_number"))],
                [_p("聯絡人"), _p(customer.get("contact_name")), _p("報價日期"), _p(data.get("quotation_date"))],
                [_p("電話／傳真"), _p(f"{_text(customer.get('phone'))} / {_text(customer.get('fax'))}"), _p("地址"), _p(customer.get("address"))],
            ],
            [22 * mm, 100 * mm, 24 * mm, 121 * mm],
        )
    )
    headers = ["序號", "品名", "尺寸", "紙質", "顏色", "上光", "版費", "刀模費", "數量", "單價", "附註"]
    rows = [[_p(value, SMALL) for value in headers]]
    for item in data.get("items", []):
        rows.append([_p(value, SMALL) for value in [str(item.get("line_number", "")).zfill(2), item.get("product_name"), item.get("size"), item.get("paper"), item.get("color"), item.get("coating"), item.get("plate_fee"), item.get("die_fee"), item.get("quantity"), item.get("unit_price"), item.get("note")]])
    widths = [12, 48, 28, 28, 23, 23, 20, 22, 20, 20, 23]
    story.extend([Spacer(1, 4 * mm), _table(rows, [width * mm for width in widths], header=True), Spacer(1, 4 * mm), _p(f"備註：{_text(data.get('notes'))}")])
    return story


def _work_order_story(data: dict[str, Any], company: dict[str, Any]) -> list[Any]:
    customer = data.get("customer_snapshot") or {}
    story = _company_header(company, "工 作 單")
    story.append(
        _table(
            [
                [_p("客戶"), _p(f"{_text(customer.get('code'))} {_text(customer.get('name'))}"), _p("工單號"), _p(data.get("document_number"))],
                [_p("客戶單號"), _p(data.get("customer_order_number")), _p("訂購／交貨"), _p(f"{_text(data.get('order_date'))} / {_text(data.get('delivery_date'))}")],
                [_p("品名"), _p(data.get("product_name")), _p("數量"), _p(data.get("order_quantity"))],
                [_p("規格補充"), _p(data.get("specification")), _p("電話"), _p(customer.get("phone"))],
            ],
            [24 * mm, 66 * mm, 24 * mm, 62 * mm],
        )
    )
    paper_rows = [[_p(v, SMALL) for v in ["備紙", "供應商", "紙質", "紙廠", "尺寸", "數量", "備註"]]]
    names = {"face": "面紙", "back": "底紙", "flute": "浪紙"}
    for paper in data.get("papers", []):
        paper_rows.append([_p(v, SMALL) for v in [names.get(paper.get("type"), paper.get("type")), paper.get("vendor"), paper.get("paper"), paper.get("mill"), paper.get("size"), paper.get("quantity"), paper.get("note")]])
    story.extend([Spacer(1, 3 * mm), _table(paper_rows, [17 * mm, 27 * mm, 27 * mm, 25 * mm, 27 * mm, 22 * mm, 31 * mm], header=True)])
    spec = data.get("print_specification") or {}
    front, back = spec.get("front") or {}, spec.get("back") or {}
    def colors_of(side: dict[str, Any]) -> str:
        return " ".join(
            code.upper() for code in ("c", "m", "y", "k") if side.get(code)
        ) or "-"
    story.extend([Spacer(1, 3 * mm), _table([[ _p("印刷規格"), _p(f"尺寸 {_text(spec.get('length'))} x {_text(spec.get('width'))} | K數 {_text(spec.get('k_count'))} | 模數 {_text(spec.get('imposition_count'))} | 印刷量 {_text(spec.get('print_quantity'))} | ±量 {_text(spec.get('variance'))}")], [_p("正面"), _p(f"{colors_of(front)} | 特別色 {_text(front.get('special_colors'))}")], [_p("反面"), _p(f"{colors_of(back)} | 特別色 {_text(back.get('special_colors'))}")]], [24 * mm, 152 * mm])])
    printable = {"plate", "proof", "printing", "coating", "mounting", "die_cutting", "finishing", "gluing", "other"}
    process_rows = [[_p(v, SMALL) for v in ["製程", "協力廠", "內容"]]]
    for process in data.get("processes", []):
        if process.get("code") in printable:
            details = "／".join(_text(process.get(key)) for key in ("content", "coating_type", "die_number", "packing") if process.get(key))
            process_rows.append([_p(process.get("name"), SMALL), _p(process.get("vendor"), SMALL), _p(details, SMALL)])
    story.extend([Spacer(1, 3 * mm), _table(process_rows, [28 * mm, 48 * mm, 100 * mm], header=True), Spacer(1, 3 * mm), _p(f"備註：{_text(data.get('notes'))}")])
    attachments = data.get("print_attachments") or []
    if attachments:
        story.extend([Spacer(1, 4 * mm), _p("附件圖稿")])
    for attachment in attachments:
        story.append(_p(attachment.get("filename"), SMALL))
        if str(attachment.get("mime_type", "")).startswith("image/"):
            image = Image(BytesIO(attachment["content"]))
            image._restrictSize(165 * mm, 90 * mm)
            story.extend([image, Spacer(1, 3 * mm)])
    return story


def _shipment_story(data: dict[str, Any], company: dict[str, Any]) -> list[Any]:
    story = _company_header(company, "出 貨 單")
    story.append(_table([[_p("出貨單號"), _p(data.get("document_number")), _p("出貨日期"), _p(data.get("shipment_date"))], [_p("客戶"), _p(data.get("customer_name")), _p("送貨地址"), _p(data.get("delivery_address"))]], [25 * mm, 55 * mm, 25 * mm, 71 * mm]))
    rows = [[_p(v, SMALL) for v in ["項次", "工單／客戶單號", "品名／規格", "正式量", "備品量", "交付合計"]]]
    for item in data.get("items", []):
        rows.append([_p(v, SMALL) for v in [item.get("line_no"), f"{_text(item.get('work_order_document_number'))}\n{_text(item.get('customer_order_number'))}", f"{_text(item.get('product_name'))}\n{_text(item.get('specification'))}", item.get("delivered_quantity"), item.get("spare_quantity"), item.get("inventory_consumed_quantity")]])
    story.extend([Spacer(1, 4 * mm), _table(rows, [13 * mm, 42 * mm, 65 * mm, 19 * mm, 19 * mm, 22 * mm], header=True), Spacer(1, 4 * mm), _p(f"備註：{_text(data.get('notes'))}"), Spacer(1, 12 * mm), _p("出貨人員：________________    客戶簽收：________________", RIGHT)])
    return story


def _statement_story(data: dict[str, Any], company: dict[str, Any]) -> list[Any]:
    story = _company_header(company, "對 帳 單")
    story.append(_table([[_p("對帳單號"), _p(data.get("document_number")), _p("日期"), _p(data.get("statement_date"))], [_p("客戶"), _p(data.get("customer_name")), _p("期間"), _p(f"{_text(data.get('period_from'))} - {_text(data.get('period_to'))}")]], [25 * mm, 55 * mm, 25 * mm, 71 * mm]))
    rows = [[_p(v, SMALL) for v in ["項次", "內容", "數量", "單價", "版費", "刀模費", "金額"]]]
    for item in data.get("items", []):
        rows.append([_p(v, SMALL) for v in [item.get("line_no"), item.get("content"), item.get("quantity"), item.get("unit_price"), item.get("plate_fee"), item.get("die_fee"), item.get("amount")]])
    totals = [[_p("未稅"), _p(data.get("subtotal_before_rounding")), _p("取整"), _p(data.get("rounding_adjustment")), _p("稅額"), _p(data.get("tax_amount")), _p("總額"), _p(data.get("grand_total"))]]
    story.extend([Spacer(1, 4 * mm), _table(rows, [13 * mm, 67 * mm, 20 * mm, 20 * mm, 19 * mm, 19 * mm, 23 * mm], header=True), Spacer(1, 4 * mm), _table(totals, [16 * mm, 27 * mm] * 4), Spacer(1, 3 * mm), _p(f"計稅：{'啟用 ' + _text(data.get('tax_rate_percent')) + '%' if data.get('tax_enabled') else '不計稅'}"), _p(f"備註：{_text(data.get('notes'))}")])
    return story


def render_document_pdf(document_type: str, data: dict[str, Any], company: dict[str, Any]) -> bytes:
    page_size = landscape(A4) if document_type == "quotation" else A4
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=page_size, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm, bottomMargin=15 * mm, title=_text(data.get("document_number")), author=_text(company.get("name")))
    builders = {"quotation": _quotation_story, "work_order": _work_order_story, "shipment": _shipment_story, "statement": _statement_story}

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(FONT, 7)
        canvas.drawRightString(page_size[0] - 15 * mm, 8 * mm, f"第 {doc.page} 頁")
        canvas.restoreState()

    document.build(builders[document_type](data, company), onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
