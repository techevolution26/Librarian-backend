from datetime import datetime, timezone

from app.models.creator_rights_declaration import (
    CREATOR_RIGHTS_BASIS,
    CreatorRightsDeclaration,
)
from app.schemas.creator_rights import CreatorRightsDeclarationCreate


def test_rights_declaration_attestation_is_explicit_input():
    declaration = CreatorRightsDeclarationCreate(
        rights_basis="original_author",
        rights_holder_name="Jane Writer",
        rights_statement="I hold the rights needed for the declared permissions.",
        hosting_allowed=True,
        public_display_allowed=True,
        download_allowed=False,
        redistribution_allowed=False,
        commercial_use_allowed=False,
        derivative_use_allowed=False,
    )
    assert declaration.attestation_acknowledged is False


def test_rights_declaration_normalizes_and_accepts_explicit_scope():
    declaration = CreatorRightsDeclarationCreate(
        rights_basis=" original_author ",
        rights_holder_name=" Jane Writer ",
        rights_statement=" I hold the relevant rights. ",
        territory=" Kenya ",
        hosting_allowed=True,
        public_display_allowed=True,
        download_allowed=False,
        redistribution_allowed=False,
        commercial_use_allowed=False,
        derivative_use_allowed=False,
        attestation_acknowledged=True,
    )
    assert declaration.rights_basis == "original_author"
    assert declaration.rights_holder_name == "Jane Writer"
    assert declaration.rights_statement == "I hold the relevant rights."
    assert declaration.territory == "Kenya"
    assert declaration.hosting_allowed is True
    assert declaration.download_allowed is False


def test_rights_basis_vocabulary_is_explicit():
    assert CREATOR_RIGHTS_BASIS == {
        "original_author",
        "copyright_holder",
        "authorized_representative",
        "licensed",
        "public_domain",
        "other",
    }


def test_rights_declaration_is_versioned_and_auditable():
    row = CreatorRightsDeclaration(
        id=1,
        submission_id=10,
        creator_account_id=3,
        version=2,
        rights_basis="licensed",
        rights_holder_name="Rights Holder",
        rights_statement="Licensed for the stated scope.",
        hosting_allowed=True,
        public_display_allowed=True,
        download_allowed=False,
        redistribution_allowed=False,
        commercial_use_allowed=False,
        derivative_use_allowed=False,
        attestation_text="I declare...",
        status="active",
        declared_by_user_id=7,
        declared_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    assert row.version == 2
    assert row.status == "active"
    assert row.declared_by_user_id == 7
