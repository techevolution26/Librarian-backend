from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.creator import get_public_creator_profile
from app.schemas.creator import CreatorPublicProfileRead


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def unique(self):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, account, books=()):
        self.account = account
        self.books = books

    def scalar(self, _query):
        return self.account

    def scalars(self, _query):
        return FakeScalarResult(self.books)


def creator(**overrides):
    values = {
        "id": 7,
        "display_name": "Jane Writer",
        "slug": "jane-writer",
        "bio": "A public author identity.",
        "website_url": "https://example.com",
        "profile_image_url": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def book(**overrides):
    values = {
        "id": 11,
        "title": "The Archive",
        "author": "Jane Writer",
        "cover": "/static/covers/archive.jpg",
        "description": "A published work.",
        "pages": 120,
        "genres": ["History", "Archive"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_public_profile_returns_identity_and_published_catalog_only() -> None:
    result = get_public_creator_profile("jane-writer", FakeDB(creator(), [book()]))

    assert isinstance(result, CreatorPublicProfileRead)
    assert result.slug == "jane-writer"
    assert result.display_name == "Jane Writer"
    assert len(result.books) == 1
    assert result.books[0].title == "The Archive"
    assert result.books[0].genre == ["History", "Archive"]


def test_public_profile_does_not_expose_creator_user_id_or_private_fields() -> None:
    result = get_public_creator_profile("jane-writer", FakeDB(creator(), []))
    payload = result.model_dump()

    assert "user_id" not in payload
    assert "status" not in payload
    assert "is_public" not in payload
    assert "books" in payload


def test_unavailable_creator_profile_returns_not_found() -> None:
    with pytest.raises(HTTPException) as exc:
        get_public_creator_profile("missing", FakeDB(None))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Creator profile not found"
