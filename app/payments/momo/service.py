from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from typing import Any

import httpx

from app.config import get_settings


def _hmac_sha256_hex(secret_key: str, raw: str) -> str:
    return hmac.new(secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


async def create_momo_payment(
    *,
    order_id: str,
    amount_vnd: int,
    order_info: str,
    redirect_url: str,
    ipn_url: str,
    request_type: str,
    extra_data: str = "",
) -> dict[str, Any]:
    """
    Minimal MoMo create-payment call.
    Notes:
    - request_type: commonly 'payWithATM' or 'captureWallet' (depends on your MoMo product).
    - signature string format is per MoMo docs; keep stable and unit-testable.
    """
    settings = get_settings()
    if not (settings.momo_partner_code and settings.momo_access_key and settings.momo_secret_key):
        raise RuntimeError("MoMo credentials are not configured in env")
    if not settings.momo_endpoint:
        raise RuntimeError("MoMo endpoint is not configured in env")

    request_id = str(uuid.uuid4())
    raw_extra = extra_data
    # Many integrations base64 encode extraData; we keep it configurable but default to empty string.
    extra_data_encoded = raw_extra if raw_extra else ""

    raw_signature = (
        f"accessKey={settings.momo_access_key}"
        f"&amount={amount_vnd}"
        f"&extraData={extra_data_encoded}"
        f"&ipnUrl={ipn_url}"
        f"&orderId={order_id}"
        f"&orderInfo={order_info}"
        f"&partnerCode={settings.momo_partner_code}"
        f"&redirectUrl={redirect_url}"
        f"&requestId={request_id}"
        f"&requestType={request_type}"
    )
    signature = _hmac_sha256_hex(settings.momo_secret_key, raw_signature)

    body: dict[str, Any] = {
        "partnerCode": settings.momo_partner_code,
        "accessKey": settings.momo_access_key,
        "requestId": request_id,
        "amount": amount_vnd,
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": redirect_url,
        "ipnUrl": ipn_url,
        "extraData": extra_data_encoded,
        "requestType": request_type,
        "signature": signature,
        "lang": "vi",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(str(settings.momo_endpoint), json=body)
        resp.raise_for_status()
        return resp.json()


def verify_momo_ipn_signature(payload: dict[str, Any]) -> bool:
    """
    Verify IPN signature. The exact raw string ordering depends on MoMo IPN spec.
    We'll implement the common v2 ordering (must match the fields MoMo sends).
    """
    settings = get_settings()
    if not settings.momo_secret_key:
        return False

    signature = payload.get("signature")
    if not isinstance(signature, str) or not signature:
        return False

    # Common fields (may vary). We include keys defensively as empty string if missing.
    def g(k: str) -> str:
        v = payload.get(k)
        return "" if v is None else str(v)

    raw = (
        f"accessKey={g('accessKey')}"
        f"&amount={g('amount')}"
        f"&extraData={g('extraData')}"
        f"&message={g('message')}"
        f"&orderId={g('orderId')}"
        f"&orderInfo={g('orderInfo')}"
        f"&orderType={g('orderType')}"
        f"&partnerCode={g('partnerCode')}"
        f"&payType={g('payType')}"
        f"&requestId={g('requestId')}"
        f"&responseTime={g('responseTime')}"
        f"&resultCode={g('resultCode')}"
        f"&transId={g('transId')}"
    )
    expected = _hmac_sha256_hex(settings.momo_secret_key, raw)
    return hmac.compare_digest(expected, signature)

