from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, Field


class MomoCheckoutRequest(BaseModel):
    packageCode: str
    returnUrl: AnyHttpUrl
    notifyUrl: AnyHttpUrl | None = None
    mode: str = Field(default="redirect", pattern="^(redirect|qr)$")
    idempotencyKey: str | None = None


class MomoCheckoutResponse(BaseModel):
    orderId: str
    paymentId: str
    payUrl: str | None = None
    deeplink: str | None = None
    qrCodeUrl: str | None = None

