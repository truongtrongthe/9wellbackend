from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class PortalPrivacy(BaseModel):
    panicUrl: str = "https://www.google.com"
    disguise: bool = False


class PortalProfileOut(BaseModel):
    user_id: str
    nickname: str
    pin_hash: str | None = None
    plan_code: str = "none"
    program_started_at: str | None = None
    current_week: int = 1
    week_done: dict[str, Any] = Field(default_factory=dict)
    privacy: PortalPrivacy = Field(default_factory=PortalPrivacy)
    client_code: str = ""
    trainer_stats: dict[str, Any] = Field(default_factory=dict)


class PortalCheckinOut(BaseModel):
    id: str
    week_number: int
    mood: str | None = None
    freq: str | None = None
    control: str | None = None
    notes: str | None = None
    created_at: str


class PortalMeResponse(BaseModel):
    profile: PortalProfileOut
    checkins: list[PortalCheckinOut] = Field(default_factory=list)
    latest_quiz: dict[str, Any] | None = None


class PortalRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    pin_hash: str | None = None


class PortalProfileUpdate(BaseModel):
    nickname: str | None = None
    pin_hash: str | None = None
    plan_code: str | None = None
    program_started_at: str | None = None
    current_week: int | None = Field(default=None, ge=1, le=8)
    week_done: dict[str, Any] | None = None
    privacy: PortalPrivacy | None = None
    trainer_stats: dict[str, Any] | None = None


class PortalQuizSubmit(BaseModel):
    answers: list[int]
    score: int
    score_max: int | None = None
    max: int | None = None
    profile_text: str = ""
    profile: str | None = None
    recommended_plan: str = ""
    plan: str | None = None

    def payload(self) -> dict:
        return {
            "answers": self.answers,
            "score": self.score,
            "score_max": self.score_max if self.score_max is not None else (self.max or 0),
            "profile_text": self.profile_text or (self.profile or ""),
            "recommended_plan": self.recommended_plan or (self.plan or "start"),
        }


class PortalCheckinCreate(BaseModel):
    week_number: int = Field(ge=1, le=8)
    mood: str | None = None
    freq: str | None = None
    control: str | None = None
    notes: str | None = None


class SepayConfig(BaseModel):
    bank: str = "Techcombank"
    account: str = "1933 9999"
    holder: str = "NGUYEN DINH DUONG"
    qrImg: str = "/assets/payment/techcombank-qr.jpg"


class PortalConfigOut(BaseModel):
    zaloLink: str = ""
    trainerUrl: str = "/trainer"
    gameUrl: str = "/game"
    hubUrl: str = "/blog"
    courseUrl: str = "/learn"
    accessCodes: list[str] = Field(default_factory=lambda: ["9WELLHIM"])
    introYtid: str = ""
    demoVideoYtid: str = ""
    sepay: SepayConfig = Field(default_factory=SepayConfig)


class PortalConfigUpdate(BaseModel):
    zaloLink: str | None = None
    trainerUrl: str | None = None
    gameUrl: str | None = None
    hubUrl: str | None = None
    courseUrl: str | None = None
    accessCodes: list[str] | None = None
    introYtid: str | None = None
    demoVideoYtid: str | None = None
    sepay: SepayConfig | None = None


class ShopOrderItem(BaseModel):
    id: str = ""
    name: str
    qty: int = 1
    price: int = 0


class ShopOrderRequest(BaseModel):
    name: str
    phone: str
    address: str
    note: str = ""
    total: int
    items: list[ShopOrderItem] = Field(default_factory=list)
