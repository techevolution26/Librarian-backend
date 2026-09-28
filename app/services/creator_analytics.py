from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.creator_book_submission import CreatorBookSubmission
from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_lifetime_access import CreatorLifetimeAccess
from app.models.creator_paid_book import CreatorPaidBook
from app.models.library_item import LibraryItem
from app.schemas.creator_analytics import CreatorAnalyticsRead, CreatorBookAnalyticsRead


READER_ACTIVITY_WINDOW_DAYS = 30


def build_creator_analytics(db: Session, creator_account_id: int) -> CreatorAnalyticsRead:
    submissions = db.execute(
        select(CreatorBookSubmission.status, func.count(CreatorBookSubmission.id))
        .where(CreatorBookSubmission.creator_account_id == creator_account_id)
        .group_by(CreatorBookSubmission.status)
    ).all()
    submission_counts = {status: count for status, count in submissions}

    hosted_books = db.scalars(
        select(CreatorHostedBook)
        .where(CreatorHostedBook.creator_account_id == creator_account_id)
        .join(Book, Book.id == CreatorHostedBook.book_id)
        .order_by(CreatorHostedBook.created_at.desc())
    ).all()

    active_cutoff = datetime.now(timezone.utc) - timedelta(days=READER_ACTIVITY_WINDOW_DAYS)
    books: list[CreatorBookAnalyticsRead] = []
    all_reader_count = 0
    all_active_reader_count = 0
    all_completed_reader_count = 0
    all_progress_sum = 0.0
    all_progress_count = 0
    all_lifetime_owner_count = 0
    active_paid_offer_count = 0

    for hosted in hosted_books:
        book_id = hosted.book_id

        reader_count = db.scalar(
            select(func.count(LibraryItem.id)).where(LibraryItem.book_id == book_id)
        ) or 0
        active_reader_count = db.scalar(
            select(func.count(LibraryItem.id)).where(
                LibraryItem.book_id == book_id,
                LibraryItem.last_read_at.is_not(None),
                LibraryItem.last_read_at >= active_cutoff,
            )
        ) or 0
        completed_reader_count = db.scalar(
            select(func.count(LibraryItem.id)).where(
                LibraryItem.book_id == book_id,
                LibraryItem.finished_at.is_not(None),
            )
        ) or 0
        average_progress = db.scalar(
            select(func.avg(LibraryItem.progress)).where(LibraryItem.book_id == book_id)
        )
        average_progress_value = round(float(average_progress or 0), 1)

        lifetime_owner_count = db.scalar(
            select(func.count(CreatorLifetimeAccess.id))
            .where(
                CreatorLifetimeAccess.hosted_book_id == hosted.id,
                CreatorLifetimeAccess.status == "active",
            )
        ) or 0
        paid_offer_active = db.scalar(
            select(CreatorPaidBook.id).where(
                CreatorPaidBook.hosted_book_id == hosted.id,
                CreatorPaidBook.status == "active",
            )
        ) is not None

        books.append(
            CreatorBookAnalyticsRead(
                hosted_book_id=hosted.id,
                book_id=book_id,
                title=hosted.book.title,
                status=hosted.status,
                reader_count=reader_count,
                active_reader_count_30d=active_reader_count,
                completed_reader_count=completed_reader_count,
                average_progress_percent=average_progress_value,
                lifetime_owner_count=lifetime_owner_count,
                paid_offer_active=paid_offer_active,
            )
        )

        all_reader_count += reader_count
        all_active_reader_count += active_reader_count
        all_completed_reader_count += completed_reader_count
        all_progress_sum += average_progress_value * reader_count
        all_progress_count += reader_count
        all_lifetime_owner_count += lifetime_owner_count
        if paid_offer_active:
            active_paid_offer_count += 1

    overall_average_progress = (
        round(all_progress_sum / all_progress_count, 1) if all_progress_count else 0.0
    )

    return CreatorAnalyticsRead(
        submission_count=sum(submission_counts.values()),
        submitted_count=submission_counts.get("submitted", 0),
        under_review_count=submission_counts.get("under_review", 0),
        changes_requested_count=submission_counts.get("changes_requested", 0),
        hosted_book_count=len(hosted_books),
        active_paid_offer_count=active_paid_offer_count,
        lifetime_owner_count=all_lifetime_owner_count,
        reader_count=all_reader_count,
        active_reader_count_30d=all_active_reader_count,
        completed_reader_count=all_completed_reader_count,
        average_progress_percent=overall_average_progress,
        books=books,
    )
