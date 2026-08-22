"""Generate PDF reports for interrogation results."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak,
)

AMBER = colors.HexColor("#F0883E")
DARK = colors.HexColor("#0E1116")
MUTED = colors.HexColor("#8B949E")
GREEN = colors.HexColor("#3FB950")
RED = colors.HexColor("#F85149")
YELLOW = colors.HexColor("#D29922")


def _status_color(status: str):
    return {"OK": GREEN, "WARNING": YELLOW, "ERROR": RED}.get(status, MUTED)


def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Kicker", fontName="Helvetica-Bold", fontSize=8,
                              textColor=AMBER, leading=10, spaceAfter=2))
    styles.add(ParagraphStyle(name="Title2", fontName="Helvetica-Bold", fontSize=20,
                              textColor=DARK, leading=24, spaceAfter=4))
    styles.add(ParagraphStyle(name="Meta", fontName="Helvetica", fontSize=9,
                              textColor=MUTED, leading=12, spaceAfter=10))
    styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=10,
                              textColor=DARK, leading=14, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle(name="Body2", fontName="Helvetica", fontSize=10,
                              textColor=DARK, leading=14))
    return styles


def _header(styles):
    return [
        Paragraph("EXPORT 7 AI · CONTROL CENTER", styles["Kicker"]),
        Paragraph("Laporan Interogasi Server", styles["Title2"]),
    ]


def _summary_table(report: Dict[str, Any]):
    rows = [
        ["Koneksi Server", report["connection"]],
        ["API", report["api"]],
        ["Database", report["database"]],
        ["Job Aktif", str(report["active_jobs"])],
        ["Job Berhasil", str(report["successful_jobs"])],
        ["Job Gagal", str(report["failed_jobs"])],
    ]
    tbl = Table(rows, colWidths=[70 * mm, 90 * mm])
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK),
        ("FONT", (1, 0), (1, -1), "Helvetica-Bold", 10),
        ("BOX", (0, 0), (-1, -1), 0.5, MUTED),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for idx in range(3):
        style.append(("TEXTCOLOR", (1, idx), (1, idx), _status_color(rows[idx][1])))
    tbl.setStyle(TableStyle(style))
    return tbl


def _ai_table(report: Dict[str, Any]):
    header = ["AI", "Nama", "Status"]
    rows = [header] + [[a["agent_id"], a["name"], a["status"]] for a in report.get("ai", [])]
    tbl = Table(rows, colWidths=[25 * mm, 95 * mm, 40 * mm])
    style = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 0), AMBER),
        ("TEXTCOLOR", (0, 0), (-1, 0), DARK),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 10),
        ("BOX", (0, 0), (-1, -1), 0.5, MUTED),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for idx, ai in enumerate(report.get("ai", []), start=1):
        style.append(("TEXTCOLOR", (2, idx), (2, idx), _status_color(ai["status"])))
        style.append(("FONT", (2, idx), (2, idx), "Helvetica-Bold", 10))
    tbl.setStyle(TableStyle(style))
    return tbl


def _audit_table(logs: List[Dict[str, Any]]):
    if not logs:
        return Paragraph("Tidak ada aktivitas 24 jam terakhir.", getSampleStyleSheet()["BodyText"])
    header = ["Waktu", "Aksi", "Detail", "Aktor"]
    rows = [header]
    for l in logs:
        try:
            ts = datetime.fromisoformat(str(l["created_at"]).replace("Z", "+00:00")).strftime("%d/%m %H:%M")
        except Exception:
            ts = "-"
        rows.append([ts, l.get("action", ""), (l.get("detail", "") or "")[:60], l.get("actor", "")])
    tbl = Table(rows, colWidths=[25 * mm, 35 * mm, 75 * mm, 25 * mm])
    tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#161B22")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("BOX", (0, 0), (-1, -1), 0.5, MUTED),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _signature(styles, actor_name: str, actor_role: str):
    now = datetime.now().strftime("%d %B %Y · %H:%M WIB")
    box = Table([
        [Paragraph("<b>Diperiksa oleh</b>", styles["Body2"])],
        [Paragraph(actor_name or "-", styles["Body2"])],
        [Paragraph(f"<font color='#8B949E'>{actor_role or ''}</font>", styles["Body2"])],
        [Paragraph(f"<font color='#8B949E'>{now}</font>", styles["Body2"])],
        [Paragraph("<font color='#F0883E'>—— tanda tangan digital ——</font>", styles["Body2"])],
    ], colWidths=[70 * mm])
    box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, AMBER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return box


def build_pdf(mode: str, report: Dict[str, Any], actor: Dict[str, Any], logs: List[Dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title="Laporan Interogasi Export 7 AI")
    styles = _base_styles()
    story: List[Any] = []
    story.extend(_header(styles))
    story.append(Paragraph(
        f"Dihasilkan otomatis · {datetime.now().strftime('%d %B %Y %H:%M')}",
        styles["Meta"],
    ))
    story.append(Paragraph("RINGKASAN SISTEM", styles["Section"]))
    story.append(_summary_table(report))
    story.append(Paragraph("STATUS 7 AI", styles["Section"]))
    story.append(_ai_table(report))
    story.append(Paragraph("ERROR TERAKHIR", styles["Section"]))
    story.append(Paragraph(report.get("last_error") or "Tidak ada error tercatat.", styles["Body2"]))

    if mode == "detailed":
        story.append(PageBreak())
        story.extend(_header(styles))
        story.append(Paragraph("AUDIT LOG · 24 JAM TERAKHIR", styles["Section"]))
        story.append(_audit_table(logs))

    story.append(Spacer(1, 12 * mm))
    story.append(_signature(styles, actor.get("name", "-"), actor.get("role", "")))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
