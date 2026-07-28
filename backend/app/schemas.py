from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

class UserSignup(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str

    class Config:
        from_attributes = True


class UploadOut(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    status: str

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v)

    @field_validator("status", mode="before")
    @classmethod
    def _stringify_status(cls, v):
        return v.value if hasattr(v, "value") else v


class TransactionOut(BaseModel):
    id: str
    date: datetime
    merchant: str
    normalized_merchant: str
    amount: float
    category: str
    category_source: str

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v)

    @field_validator("category_source", mode="before")
    @classmethod
    def _stringify_source(cls, v):
        return v.value if hasattr(v, "value") else v


class AnomalyOut(BaseModel):
    id: str
    type: str
    reason: str
    evidence: dict
    severity: str
    transaction_id: str | None


class DashboardSummary(BaseModel):
    upload_id: str
    total_transactions: int
    total_spent: float
    total_income: float
    by_category: dict[str, float]


class NarrativeOut(BaseModel):
    upload_id: str
    narrative: str