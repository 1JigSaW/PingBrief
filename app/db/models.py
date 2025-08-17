import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    Integer,
    UniqueConstraint,
    Index,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    telegram_id: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=True,
        comment="Telegram user ID, if registered via bot",
    )

    username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Telegram or web username",
    )

    first_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="User's first name",
    )

    last_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="User's last name",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Active flag",
    )

    premium_until: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Premium access valid until (UTC)",
    )

    preferred_language: Mapped[str | None] = mapped_column(
        String(8),
        ForeignKey("languages.code"),
        nullable=True,
    )

    timezone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    digests: Mapped[list["Digest"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Human-friendly name",
    )

    url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="RSS feed URL or API endpoint",
    )

    default_language: Mapped[str] = mapped_column(
        String(8),
        default="en",
        nullable=False,
        comment="Default language code (ISO 639-1)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable/disable source",
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )

class Language(Base, TimestampMixin):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(
        String(8),
        primary_key=True
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable/disable this subscription",
    )

    user: Mapped["User"] = relationship(
        back_populates="subscriptions",
    )

    source: Mapped["Source"] = relationship(
        back_populates="subscriptions",
    )

    digests: Mapped[list["Digest"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    language: Mapped[str] = mapped_column(
        String(8),
        ForeignKey("languages.code"),
        nullable=False
    )

    language_rel: Mapped["Language"] = relationship(
        back_populates="subscriptions"
    )

Language.subscriptions = relationship(
    "Subscription",
    back_populates="language_rel",
    cascade="all, delete-orphan"
)

Index("ix_subscriptions_user_id", Subscription.user_id)
UniqueConstraint(Subscription.user_id, Subscription.source_id, name="uq_subscription_user_source")


class DigestStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Digest(Base, TimestampMixin):
    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="Original article title",
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="LLM-generated summary",
    )

    url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Link to the full article",
    )

    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="When this digest should be sent",
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Actual send timestamp (populated upon send)",
    )

    status: Mapped[DigestStatus] = mapped_column(
        SAEnum(DigestStatus),
        default=DigestStatus.PENDING,
        nullable=False,
        comment="Delivery status",
    )

    subscription: Mapped["Subscription"] = relationship(
        back_populates="digests",
    )

    user: Mapped["User"] = relationship(
        back_populates="digests",
    )

    telegram_message_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_digests_status_scheduled_for", "status", "scheduled_for"),
    )

class NewsItem(Base, TimestampMixin):
    __tablename__ = "news_items"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="id news form api",
    )
    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full article content",
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="LLM-generated summary",
    )
    url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Time to schedule",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_news_item_source_external"),
        Index("ix_news_items_source_fetched", "source_id", "fetched_at"),
    )


class NewsItemTranslation(Base, TimestampMixin):
    __tablename__ = "news_item_translations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    news_item_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("news_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    language: Mapped[str] = mapped_column(
        String(8),
        ForeignKey("languages.code"),
        nullable=False,
        comment="Target language (ISO 639-1)",
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="libretranslate",
        comment="Translation provider",
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Hash of base summary to invalidate stale translations",
        index=True,
    )

    summary_translated: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Translated summary text",
    )

    __table_args__ = (
        UniqueConstraint("news_item_id", "language", "provider", name="uq_news_item_translation"),
    )


class PaymentStatus(str, Enum):
    PAID = "paid"
    FAILED = "failed"


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    telegram_payment_charge_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    provider_payment_charge_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    payload: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(8),
        default="XTR",
        nullable=False,
    )

    amount_stars: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    price_stars: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    term_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus),
        default=PaymentStatus.PAID,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="payments",
    )

User.payments = relationship(
    "Payment",
    back_populates="user",
    cascade="all, delete-orphan",
)

Index("ix_payments_user_id", Payment.user_id)
