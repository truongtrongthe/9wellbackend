from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from supabase import Client

from app.auth.security import get_current_user
from app.db.supabase_client import get_supabase
from app.payments.momo.models import MomoCheckoutRequest, MomoCheckoutResponse
from app.payments.momo.service import create_momo_payment, verify_momo_ipn_signature
from app.membership.subscription_actions import activate_or_extend_subscription
from app.payments.repository import (
    create_order,
    create_payment,
    get_order_by_idempotency_key,
    get_package_by_code,
)

router = APIRouter()


@router.post("/checkout/momo", response_model=MomoCheckoutResponse)
async def momo_checkout(
    body: MomoCheckoutRequest,
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> MomoCheckoutResponse:
    package = get_package_by_code(client, body.packageCode)
    if not package or package.get("status") != "active":
        raise HTTPException(status_code=404, detail="Package not found")

    if body.idempotencyKey:
        existing = get_order_by_idempotency_key(client, body.idempotencyKey)
        if existing:
            # Return last payment for that order if present; otherwise fail fast.
            pay = (
                client.table("payments")
                .select("*")
                .eq("order_id", existing["id"])
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if pay.data:
                p = pay.data[0]
                return MomoCheckoutResponse(
                    orderId=str(existing["id"]),
                    paymentId=str(p["id"]),
                    payUrl=p.get("pay_url"),
                    deeplink=p.get("deeplink"),
                    qrCodeUrl=p.get("qr_code_url"),
                )
            raise HTTPException(status_code=409, detail="Idempotency key already used")

    order = create_order(
        client,
        user_id=str(user["id"]),
        package_id=str(package["id"]),
        amount_vnd=int(package["price_vnd"]),
        idempotency_key=body.idempotencyKey,
    )

    # MoMo requestType varies by product; keep a sensible default.
    request_type = "captureWallet" if body.mode in ("redirect", "qr") else "captureWallet"
    ipn_url = str(body.notifyUrl or body.returnUrl)
    try:
        momo_resp = await create_momo_payment(
            order_id=str(order["id"]),
            amount_vnd=int(order["amount_vnd"]),
            order_info=f"9well membership {package['code']}",
            redirect_url=str(body.returnUrl),
            ipn_url=ipn_url,
            request_type=request_type,
            extra_data="",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    payment = create_payment(
        client,
        order_id=str(order["id"]),
        provider="momo",
        status="created",
        pay_url=momo_resp.get("payUrl") or momo_resp.get("payUrlWeb") or momo_resp.get("payUrl"),
        deeplink=momo_resp.get("deeplink") or momo_resp.get("deeplinkMiniApp"),
        qr_code_url=momo_resp.get("qrCodeUrl"),
        provider_payment_id=str(momo_resp.get("requestId") or ""),
        raw_create_response=momo_resp if isinstance(momo_resp, dict) else None,
    )

    return MomoCheckoutResponse(
        orderId=str(order["id"]),
        paymentId=str(payment["id"]),
        payUrl=payment.get("pay_url"),
        deeplink=payment.get("deeplink"),
        qrCodeUrl=payment.get("qr_code_url"),
    )


@router.post("/webhooks/momo/ipn")
async def momo_ipn(request: Request, client: Client = Depends(get_supabase)) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    signature_ok = verify_momo_ipn_signature(payload)
    order_id = payload.get("orderId")
    if not isinstance(order_id, str) or not order_id:
        raise HTTPException(status_code=400, detail="Missing orderId")

    # Persist raw IPN + signature validity on latest payment for this order.
    pay = (
        client.table("payments")
        .select("*")
        .eq("order_id", order_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not pay.data:
        raise HTTPException(status_code=404, detail="Payment not found for order")
    payment = pay.data[0]

    # Update payment record (idempotent overwrite)
    client.table("payments").update(
        {
            "raw_ipn_payload": payload,
            "signature_valid": signature_ok,
            "provider_payment_id": str(payload.get("transId") or payment.get("provider_payment_id") or ""),
            "updated_at": None,
        }
    ).eq("id", payment["id"]).execute()

    if not signature_ok:
        raise HTTPException(status_code=400, detail="Invalid signature")

    result_code = int(payload.get("resultCode") or -1)
    succeeded = result_code == 0

    # Order state transition (idempotent)
    new_order_status = "paid" if succeeded else "failed"
    order_resp = (
        client.table("orders")
        .update({"status": new_order_status, "updated_at": None})
        .eq("id", order_id)
        .execute()
    )
    client.table("payments").update(
        {"status": "succeeded" if succeeded else "failed", "updated_at": None}
    ).eq("id", payment["id"]).execute()

    if succeeded and order_resp.data:
        order = order_resp.data[0]
        user_id = str(order["user_id"])
        package_id = str(order["package_id"])

        pkg_resp = (
            client.table("membership_packages").select("*").eq("id", package_id).limit(1).execute()
        )
        if pkg_resp.data:
            pkg = pkg_resp.data[0]
            duration_days = int(pkg.get("duration_days") or 0)
            if duration_days > 0:
                activate_or_extend_subscription(
                    client,
                    user_id=user_id,
                    package_id=package_id,
                    duration_days=duration_days,
                    status="active",
                )

    return {"ok": True}
