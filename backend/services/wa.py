"""WhatsApp OTP adapter. Default mock — swap by setting WA_PROVIDER env var.

Supported providers:
- mock (default) — records OTP to `mock_wa_outbox` MongoDB collection & logs it.
- fonnte — https://docs.fonnte.com/api/send-message
- twilio — Twilio WhatsApp API

Config via env:
- WA_PROVIDER = mock | fonnte | twilio
- WA_SENDER_NAME (optional, default "Export 7 AI")
- Fonnte: WA_FONNTE_TOKEN
- Twilio: WA_TWILIO_SID, WA_TWILIO_TOKEN, WA_TWILIO_FROM (e.g. whatsapp:+14155238886)
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("export7ai.wa")


def _normalize(number: str) -> str:
    digits = re.sub(r"\D", "", number or "")
    if not digits:
        return ""
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    return digits


async def send_whatsapp(db: Any, to: str, message: str, purpose: str = "OTP") -> dict:
    """Deliver a WhatsApp message via the configured provider.

    Returns a small dict with provider + status. Never raises — failures
    fall back to storing the message in `mock_wa_outbox` so the flow can
    continue and the admin can pick the OTP up from Pengaturan.
    """
    provider = os.environ.get("WA_PROVIDER", "mock").lower()
    number = _normalize(to)
    sender = os.environ.get("WA_SENDER_NAME", "Export 7 AI")
    now = datetime.now(timezone.utc).isoformat()
    outbox = {
        "to": number, "raw_to": to, "message": message,
        "purpose": purpose, "provider": provider, "sender": sender,
        "created_at": now, "status": "queued",
    }

    if not number:
        outbox["status"] = "failed"
        outbox["error"] = "Nomor WhatsApp kosong"
        await db.mock_wa_outbox.insert_one(outbox.copy())
        return outbox

    try:
        if provider == "fonnte":
            token = os.environ.get("WA_FONNTE_TOKEN", "")
            if not token:
                raise RuntimeError("WA_FONNTE_TOKEN belum dikonfigurasi")
            async with httpx.AsyncClient(timeout=15) as http:
                res = await http.post(
                    "https://api.fonnte.com/send",
                    headers={"Authorization": token},
                    data={"target": number, "message": message, "countryCode": "62"},
                )
            outbox["status"] = "sent" if res.status_code == 200 else "failed"
            outbox["response"] = res.text[:400]
        elif provider == "twilio":
            sid = os.environ.get("WA_TWILIO_SID", "")
            tok = os.environ.get("WA_TWILIO_TOKEN", "")
            frm = os.environ.get("WA_TWILIO_FROM", "")
            if not (sid and tok and frm):
                raise RuntimeError("Kredensial Twilio belum lengkap")
            async with httpx.AsyncClient(timeout=15, auth=(sid, tok)) as http:
                res = await http.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                    data={"From": frm, "To": f"whatsapp:+{number}", "Body": message},
                )
            outbox["status"] = "sent" if res.status_code in (200, 201) else "failed"
            outbox["response"] = res.text[:400]
        else:
            outbox["status"] = "mock"
            logger.info("[MOCK WA → %s] %s", number, message)
    except Exception as exc:  # noqa: BLE001
        outbox["status"] = "failed"
        outbox["error"] = str(exc)[:400]
        logger.warning("WhatsApp send failed (%s): %s", provider, exc)

    await db.mock_wa_outbox.insert_one(outbox.copy())
    return outbox
