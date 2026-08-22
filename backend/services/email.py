"""Email service via Emergent-managed Resend proxy.

Guardrail-compliant:
- Recipient comes from server-side record (report_recipients per user), never
  from raw request markup.
- Subject and HTML body are server-side templates only.
- No forms/inputs, only absolute https links, no shorteners.
- Sender is the app's own brand via EMAIL_FROM_NAME.
"""
from __future__ import annotations

import base64
import ipaddress
import logging
import os
import re
from html import escape
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("export7ai.email")

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = (
    "reply with your password", "reply with the code", "send your password", "cvv",
    "send us your password", "enter your password below", "confirm your card number",
    "your full card number", "seed phrase", "recovery phrase", "verify your card",
    "social security number", "confirm your bank details",
)
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: set[str] = set()
        self.urls: list[str] = []
        self.anchors: list[tuple[str, str]] = []
        self._href: Optional[str] = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened/numeric/credential URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} ≠ real host {real!r} (G3)")


async def _post_send(payload: Dict[str, Any]) -> Optional[str]:
    key = os.environ.get("EMERGENT_EMAIL_KEY", "")
    if not key:
        raise RuntimeError("EMERGENT_EMAIL_KEY belum dikonfigurasi")
    async with httpx.AsyncClient(timeout=30) as http:
        res = await http.post(
            f"{EMAIL_BASE_URL}/api/v1/email/send",
            headers={"X-Email-Key": key},
            json=payload,
        )
    if res.status_code >= 400:
        logger.error("Email proxy error %s: %s", res.status_code, res.text[:400])
        raise RuntimeError(f"Gagal kirim email ({res.status_code})")
    try:
        return res.json().get("id")
    except Exception:
        return None


def _brand() -> str:
    return os.environ.get("EMAIL_FROM_NAME", "Export 7 AI")


def render_interrogation_email(
    report: Dict[str, Any],
    actor: Dict[str, Any],
    note: str,
    mode: str,
) -> tuple[str, str]:
    brand = escape(_brand())
    checked_at = escape(report.get("checked_at", ""))
    ai_rows = "".join(
        f'<tr><td style="padding:6px 8px;border-bottom:1px solid #eee">{escape(a["name"])}</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;font-weight:600;color:'
        f'{"#3FB950" if a["status"] == "OK" else "#D29922" if a["status"] == "WARNING" else "#F85149"}">'
        f'{escape(a["status"])}</td></tr>'
        for a in report.get("ai", [])
    )
    status_color = {
        "OK": "#3FB950", "ERROR": "#F85149", "WARNING": "#D29922",
    }
    conn_c = status_color.get(report["connection"], "#8B949E")
    api_c = status_color.get(report["api"], "#8B949E")
    db_c = status_color.get(report["database"], "#8B949E")
    note_html = (
        f'<tr><td style="padding:12px 20px;font-family:Arial,sans-serif;color:#0E1116;'
        f'background:#fff8f0;border-left:3px solid #F0883E">'
        f'<strong>Catatan admin:</strong> {escape(note)}</td></tr>'
        if note else ""
    )

    subject = f"Laporan Interogasi Server — {brand}"
    html = f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;font-family:Arial,sans-serif">
  <tr><td align="center" style="padding:24px">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e5e7eb">
      <tr><td style="background:#0E1116;padding:20px 24px">
        <div style="color:#F0883E;font-size:11px;letter-spacing:2px;font-weight:700">EXPORT OPERATIONS · CONTROL CENTER</div>
        <div style="color:#F0F2F5;font-size:22px;font-weight:800;margin-top:4px">{brand} — Laporan Interogasi</div>
      </td></tr>
      <tr><td style="padding:20px 24px">
        <p style="margin:0 0 12px 0;color:#0E1116;font-size:14px">Berikut ringkasan hasil pemeriksaan server yang dijalankan oleh
        <strong>{escape(actor.get("name", "-"))}</strong> ({escape(actor.get("role", "-"))}) pada {checked_at}.</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-collapse:collapse">
          <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666">Koneksi Server</td>
            <td style="padding:10px 12px;border-bottom:1px solid #eee;color:{conn_c};font-weight:700">{escape(report["connection"])}</td>
          </tr>
          <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666">API</td>
            <td style="padding:10px 12px;border-bottom:1px solid #eee;color:{api_c};font-weight:700">{escape(report["api"])}</td>
          </tr>
          <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666">Database</td>
            <td style="padding:10px 12px;border-bottom:1px solid #eee;color:{db_c};font-weight:700">{escape(report["database"])}</td>
          </tr>
          <tr><td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666">Job Aktif</td>
              <td style="padding:10px 12px;border-bottom:1px solid #eee">{report["active_jobs"]}</td></tr>
          <tr><td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666">Job Berhasil</td>
              <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#3FB950;font-weight:700">{report["successful_jobs"]}</td></tr>
          <tr><td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666">Job Gagal</td>
              <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#F85149;font-weight:700">{report["failed_jobs"]}</td></tr>
        </table>
        <h3 style="margin:18px 0 8px 0;color:#0E1116;font-size:14px">Status 7 AI</h3>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-collapse:collapse">
          {ai_rows}
        </table>
        <h3 style="margin:18px 0 8px 0;color:#0E1116;font-size:14px">Error Terakhir</h3>
        <p style="margin:0;color:#0E1116;font-size:13px">{escape(report.get("last_error") or "Tidak ada error tercatat.")}</p>
        <p style="margin:16px 0 0 0;color:#666;font-size:12px">Laporan lengkap ({escape(mode)}) terlampir dalam PDF · ditandatangani digital oleh admin di atas.</p>
      </td></tr>
      {note_html}
      <tr><td style="padding:14px 24px;background:#0E1116;color:#8B949E;font-size:11px">
        Email transaksional dari {brand}. Kami tidak pernah meminta password atau kode OTP via email.
      </td></tr>
    </table>
  </td></tr>
</table>
""".strip()
    return subject, html


async def send_interrogation_email(
    *,
    to: str,
    recipient_name: str,
    report: Dict[str, Any],
    actor: Dict[str, Any],
    note: str,
    mode: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> Dict[str, Any]:
    subject, html = render_interrogation_email(report, actor, note, mode)
    _assert_safe_email(subject, html)
    payload: Dict[str, Any] = {
        "to": [to],
        "subject": subject,
        "html": html,
        "from_name": _brand(),
        "attachments": [
            {
                "filename": pdf_filename,
                "content": base64.b64encode(pdf_bytes).decode(),
                "content_type": "application/pdf",
            }
        ],
    }
    reply_to = os.environ.get("EMAIL_REPLY_TO")
    if reply_to:
        payload["contact_email"] = reply_to
    message_id = await _post_send(payload)
    return {
        "status": "sent",
        "message_id": message_id,
        "recipient": to,
        "recipient_name": recipient_name,
        "subject": subject,
    }
