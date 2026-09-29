from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SubscriptionPlanFeatureLimit(Base):
    """A capability/limit configured on a subscription plan.

    ``enabled`` controls whether the feature is available. When enabled,
    ``limit_value`` is either a non-negative numeric ceiling or ``None`` for
    an explicitly unlimited feature. This is plan catalogue metadata only;
    it is not a user's subscription and does not itself grant an entitlement.
    """

    __tablename__ = "subscription_plan_feature_limits"
    __table_args__ = (
        UniqueConstraint("plan_id", "feature_key", name="uq_subscription_plan_feature_limit"),
        Index("ix_subscription_plan_feature_limits_plan_id", "plan_id"),
        Index("ix_subscription_plan_feature_limits_feature_key", "feature_key"),
        CheckConstraint("limit_value IS NULL OR limit_value >= 0", name="ck_subscription_plan_feature_limit_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    limit_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="feature_limits")


from app.models.subscription_plan import SubscriptionPlan
