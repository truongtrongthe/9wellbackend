from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.auth.security import get_current_user
from app.db.supabase_client import get_supabase
from app.payments.bank.models import BankCheckoutRequest, BankCheckoutResponse, BankSepayInfo
from app.payments.repository import (
    create_order,
    create_payment,
    get_order_by_idempotency_key,
    get_package_by_code,
    get_pending_order_for_user_package,
)
from app.portal.repository import get_portal_config

router = APIRouter()


def _sepay_info(client: Client, payment: dict | None = None) -> BankSepayInfo:
    cfg = get_portal_config(client)
    sepay = cfg.get("sepay") or {}
    return BankSepayInfo(
        bank=str(sepay.get("bank") or ""),
        account=str(sepay.get("account") or ""),
        holder=str(sepay.get("holder") or ""),
        qrImg=str(sepay.get("qrImg") or (payment or {}).get("qr_code_url") or ""),
    )


def _response(
    client: Client,
    order: dict,
    payment: dict,
    code: str,
    package: dict,
) -> BankCheckoutResponse:
    return BankCheckoutResponse(
        orderId=str(order["id"]),
        paymentId=str(payment["id"]),
        packageCode=code,
        amountVnd=int(order.get("amount_vnd") or package["price_vnd"]),
        status=str(order.get("status") or "pending"),
        transferContent=f"9WELL {code.upper()}",
        sepay=_sepay_info(client, payment),
    )


@router.post("/checkout/bank-transfer", response_model=BankCheckoutResponse)
def bank_transfer_checkout(
    body: BankCheckoutRequest,
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> BankCheckoutResponse:
    package = get_package_by_code(client, body.package_code)
    if not package or package.get("status") != "active":
        raise HTTPException(status_code=404, detail="Package not found")

    user_id = str(user["id"])
    package_id = str(package["id"])
    amount = int(package["price_vnd"])
    code = str(package["code"])

    if body.idempotency_key:
        existing = get_order_by_idempotency_key(client, body.idempotency_key)
        if existing:
            pay = (
                client.table("payments")
                .select("*")
                .eq("order_id", existing["id"])
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not pay.data:
                raise HTTPException(status_code=409, detail="Idempotency key already used")
            return _response(client, existing, pay.data[0], code, package)

    pending = get_pending_order_for_user_package(client, user_id, package_id)
    if pending:
        pay = (
            client.table("payments")
            .select("*")
            .eq("order_id", pending["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if pay.data:
            return _response(client, pending, pay.data[0], code, package)

    order = create_order(
        client,
        user_id=user_id,
        package_id=package_id,
        amount_vnd=amount,
        idempotency_key=body.idempotency_key,
    )

    cfg = get_portal_config(client)
    sepay = cfg.get("sepay") or {}
    payment = create_payment(
        client,
        order_id=str(order["id"]),
        provider="bank",
        status="processing",
        pay_url=None,
        deeplink=None,
        qr_code_url=str(sepay.get("qrImg") or ""),
        provider_payment_id=None,
        raw_create_response={"provider": "bank", "sepay": sepay},
    )
    return _response(client, order, payment, code, package)
