from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator, model_validator


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    phone: str | None = None
    provider: str
    email_verified: bool
    role: str = "user"


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str
    confirmPassword: str

    @model_validator(mode="after")
    def _passwords_match(self) -> "SignupRequest":
        if self.password != self.confirmPassword:
            raise ValueError("Passwords do not match")
        return self

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refreshToken: str


class LogoutRequest(BaseModel):
    refreshToken: str | None = None


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    refreshToken: str

