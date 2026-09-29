from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


PLAN_STATUSES = {"draft", "active", "archived"}
PLAN_BILLING_INTERVALS = {"none", "month", "year"}


class SubscriptionPlan(Base):
    """Catalog definition for a subscription plan.

    A plan is product/catalogue metadata only. It does not represent a
    customer's subscription, payment, invoice, purchase, or entitlement.
    Feature limits are configured separately as plan-level catalogue metadata.
    """

    __tablename__ = "subscription_plans"
    __table_args__ = (
        UniqueConstraint("code", name="uq_subscription_plans_code"),
        Index("ix_subscription_plans_status", "status"),
        Index("ix_subscription_plans_sort_order", "sort_order"),
        CheckConstraint("price_amount_minor >= 0", name="ck_subscription_plan_price_nonnegative"),
        CheckConstraint(
            "billing_interval IN ('none', 'month', 'year')",
            name="ck_subscription_plan_billing_interval",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_subscription_plan_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stripe_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    feature_limits: Mapped[list["SubscriptionPlanFeatureLimit"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="SubscriptionPlanFeatureLimit.feature_key"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
