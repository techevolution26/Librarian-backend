from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


INSTITUTION_STATUSES = {"active", "suspended", "archived"}
INSTITUTION_MEMBERSHIP_STATUSES = {"active", "revoked"}
INSTITUTION_MEMBER_ROLES = {"owner", "admin", "member"}
INSTITUTION_SUBSCRIPTION_STATUSES = {"active", "paused", "canceled"}


class Institution(Base):
    """Organization identity for institution-managed Librarian access."""

    __tablename__ = "institutions"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_institutions_slug"),
        Index("ix_institutions_status", "status"),
        Index("ix_institutions_owner_user_id", "owner_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner = relationship("User", foreign_keys=[owner_user_id])
    memberships = relationship("InstitutionMembership", back_populates="institution", cascade="all, delete-orphan")
    subscriptions = relationship("InstitutionSubscription", back_populates="institution", cascade="all, delete-orphan")


class InstitutionMembership(Base):
    """Membership connecting a Librarian user to an institution."""

    __tablename__ = "institution_memberships"
    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_institution_membership"),
        Index("ix_institution_memberships_user_status", "user_id", "status"),
        Index("ix_institution_memberships_institution_status", "institution_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    institution = relationship("Institution", back_populates="memberships")
    user = relationship("User")


class InstitutionSubscription(Base):
    """Provider-neutral institutional plan assignment.

    This is the local access contract for an institution. Payment/provider
    synchronization can be added later without making membership itself a
    billing record.
    """

    __tablename__ = "institution_subscriptions"
    __table_args__ = (
        Index("ix_institution_subscriptions_institution_status", "institution_id", "status"),
        Index("ix_institution_subscriptions_plan_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    institution = relationship("Institution", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan")
