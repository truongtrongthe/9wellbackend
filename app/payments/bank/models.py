from __future__ import annotations

from pydantic import BaseModel, Field


class BankCheckoutRequest(BaseModel):
    package_code: str = Field(alias="packageCode", min_length=1)
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")

    model_config = {"populate_by_name": True}


class BankSepayInfo(BaseModel):
    bank: str
    account: str
    holder: str
    qr_img: str = Field(alias="qrImg")

    model_config = {"populate_by_name": True}


class BankCheckoutResponse(BaseModel):
    order_id: str = Field(alias="orderId")
    payment_id: str = Field(alias="paymentId")
    package_code: str = Field(alias="packageCode")
    amount_vnd: int = Field(alias="amountVnd")
    status: str
    transfer_content: str = Field(alias="transferContent")
    sepay: BankSepayInfo

    model_config = {"populate_by_name": True}
