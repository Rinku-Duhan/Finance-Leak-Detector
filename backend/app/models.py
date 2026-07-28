import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------- Enums (Python-side, mapped to real Postgres ENUM types) ----------

class UploadStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CategorySource(str, enum.Enum):
    CACHE = "cache"
    RULE = "rule"
    LLM = "llm"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AnomalyType(str, enum.Enum):
    DUPLICATE_CHARGE = "duplicate_charge"
    DORMANT_SUBSCRIPTION = "dormant_subscription"
    PRICE_CREEP = "price_creep"
    CATEGORY_DRIFT = "category_drift"


# ---------- Tables ----------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    uploads: Mapped[list["Upload"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    anomalies: Mapped[list["DetectedAnomaly"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    status: Mapped[UploadStatus] = mapped_column(SAEnum(UploadStatus, name="upload_status"), default=UploadStatus.PENDING)

    user: Mapped["User"] = relationship(back_populates="uploads")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="upload", cascade="all, delete-orphan")
    anomalies: Mapped[list["DetectedAnomaly"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class MerchantCategory(Base):
    """Cache: normalized merchant -> category, avoids repeat LLM calls."""
    __tablename__ = "merchant_category"

    normalized_merchant: Mapped[str] = mapped_column(String(255), primary_key=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    merchant: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_merchant: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    category_source: Mapped[CategorySource] = mapped_column(SAEnum(CategorySource, name="category_source"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="transactions")
    upload: Mapped["Upload"] = relationship(back_populates="transactions")
    anomalies: Mapped[list["DetectedAnomaly"]] = relationship(back_populates="transaction")


class DetectedAnomaly(Base):
    __tablename__ = "detected_anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    type: Mapped[AnomalyType] = mapped_column(SAEnum(AnomalyType, name="anomaly_type"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity, name="severity"), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="anomalies")
    upload: Mapped["Upload"] = relationship(back_populates="anomalies")
    transaction: Mapped["Transaction | None"] = relationship(back_populates="anomalies")