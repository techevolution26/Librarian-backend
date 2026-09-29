from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.schemas.subscription_plan import SubscriptionPlanRead
from app.schemas.subscription_plan_feature import SubscriptionPlanFeatureLimitUpsert
from app.services.subscription_plan_features import normalize_feature_key


def test_feature_limit_supports_disabled_feature():
    row = SubscriptionPlanFeatureLimit(
        id=1,
        plan_id=2,
        feature_key="advanced_reader",
        enabled=False,
        limit_value=None,
    )
    assert row.enabled is False
    assert row.limit_value is None


def test_feature_limit_none_means_unlimited_when_enabled():
    row = SubscriptionPlanFeatureLimit(
        id=1,
        plan_id=2,
        feature_key="saved_searches",
        enabled=True,
        limit_value=None,
    )
    assert row.enabled is True
    assert row.limit_value is None


def test_feature_limit_supports_numeric_ceiling():
    row = SubscriptionPlanFeatureLimit(
        id=1,
        plan_id=2,
        feature_key="bookmark_count",
        enabled=True,
        limit_value=100,
    )
    assert row.limit_value == 100


def test_feature_key_is_normalized():
    assert normalize_feature_key("  BOOKMARK-COUNT ") == "bookmark-count"


def test_feature_key_rejects_punctuation():
    try:
        normalize_feature_key("bookmark.count")
    except ValueError:
        pass
    else:
        raise AssertionError("punctuated feature keys must be rejected")


def test_upsert_payload_normalizes_feature_key():
    payload = SubscriptionPlanFeatureLimitUpsert(
        feature_key=" Advanced_Reader ",
        enabled=True,
        limit_value=None,
    )
    assert payload.feature_key == "advanced_reader"


def test_upsert_payload_rejects_negative_limit():
    try:
        SubscriptionPlanFeatureLimitUpsert(feature_key="bookmarks", limit_value=-1)
    except Exception:
        pass
    else:
        raise AssertionError("negative feature limits must be rejected")


def test_plan_read_exposes_feature_limits_without_user_entitlement_fields():
    fields = SubscriptionPlanRead.model_fields
    assert "feature_limits" in fields
    assert "user_id" not in fields
    assert "entitlement_id" not in fields
