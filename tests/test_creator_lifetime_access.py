from app.models.creator_lifetime_access import (
    CREATOR_LIFETIME_ACCESS_SOURCES,
    CREATOR_LIFETIME_ACCESS_STATUSES,
    CreatorLifetimeAccess,
)


def test_lifetime_access_vocabulary_is_explicit():
    assert CREATOR_LIFETIME_ACCESS_STATUSES == {"active", "revoked"}
    assert CREATOR_LIFETIME_ACCESS_SOURCES == {"purchase", "manual", "admin"}


def test_lifetime_access_is_user_and_hosted_book_scoped():
    row = CreatorLifetimeAccess(user_id=8, hosted_book_id=12, status="active", access_source="purchase")
    assert row.user_id == 8
    assert row.hosted_book_id == 12
    assert row.purchase_id is None
    assert row.paid_offer_id is None


def test_lifetime_access_can_retain_paid_offer_reference():
    row = CreatorLifetimeAccess(user_id=8, hosted_book_id=12, paid_offer_id=44, access_source="purchase")
    assert row.paid_offer_id == 44
    assert row.access_source == "purchase"


def test_lifetime_access_can_reference_the_verified_purchase_that_created_it():
    row = CreatorLifetimeAccess(
        user_id=8, hosted_book_id=12, purchase_id=55, paid_offer_id=44,
        status="active", access_source="purchase"
    )
    assert row.purchase_id == 55
    assert row.paid_offer_id == 44


def test_purchase_id_is_not_the_entitlement_identifier():
    row = CreatorLifetimeAccess(user_id=8, hosted_book_id=12, purchase_id=55, status="active", access_source="purchase")
    assert not hasattr(row, "entitlement_id")


def test_admin_owned_lifetime_access_does_not_claim_a_purchase_reference():
    row = CreatorLifetimeAccess(
        user_id=8, hosted_book_id=12, purchase_id=None, paid_offer_id=44,
        status="active", access_source="admin"
    )
    assert row.purchase_id is None
