from typing import Optional
import datetime

from sqlalchemy import Date, DateTime, Float, ForeignKeyConstraint, Index, Integer, JSON, String, Text, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class Books(Base):
    __tablename__ = 'books'
    __table_args__ = (
        Index('ix_books_author', 'author'),
        Index('ix_books_id', 'id'),
        Index('ix_books_title', 'title')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    cover: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    pages: Mapped[int] = mapped_column(Integer, nullable=False)
    genre_csv: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'published'"))
    is_featured: Mapped[int] = mapped_column(TINYINT(1), nullable=False, server_default=text("'0'"))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    source_path: Mapped[Optional[str]] = mapped_column(String(500))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    archived_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    cover_path: Mapped[Optional[str]] = mapped_column(String(500))

    library_items: Mapped[list['LibraryItems']] = relationship('LibraryItems', back_populates='book')
    circle_books: Mapped[list['CircleBooks']] = relationship('CircleBooks', back_populates='book')


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index('ix_users_email', 'email', unique=True),
        Index('ix_users_id', 'id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[int] = mapped_column(TINYINT(1), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('(now())'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('(now())'))
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'USER'"))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255))

    admin_activity_logs: Mapped[list['AdminActivityLogs']] = relationship('AdminActivityLogs', back_populates='admin_user')
    circles: Mapped[list['Circles']] = relationship('Circles', back_populates='owner')
    library_items: Mapped[list['LibraryItems']] = relationship('LibraryItems', back_populates='user')
    user_connections_addressee: Mapped[list['UserConnections']] = relationship('UserConnections', foreign_keys='[UserConnections.addressee_id]', back_populates='addressee')
    user_connections_requester: Mapped[list['UserConnections']] = relationship('UserConnections', foreign_keys='[UserConnections.requester_id]', back_populates='requester')
    user_settings: Mapped[list['UserSettings']] = relationship('UserSettings', back_populates='user')
    circle_books: Mapped[list['CircleBooks']] = relationship('CircleBooks', back_populates='created_by_user')
    circle_members_invited_by_user: Mapped[list['CircleMembers']] = relationship('CircleMembers', foreign_keys='[CircleMembers.invited_by_user_id]', back_populates='invited_by_user')
    circle_members_user: Mapped[list['CircleMembers']] = relationship('CircleMembers', foreign_keys='[CircleMembers.user_id]', back_populates='user')
    circle_progress_updates: Mapped[list['CircleProgressUpdates']] = relationship('CircleProgressUpdates', back_populates='user')


class AdminActivityLogs(Base):
    __tablename__ = 'admin_activity_logs'
    __table_args__ = (
        ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL', name='admin_activity_logs_ibfk_1'),
        Index('admin_user_id', 'admin_user_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    admin_user_id: Mapped[Optional[int]] = mapped_column(Integer)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    admin_user: Mapped[Optional['Users']] = relationship('Users', back_populates='admin_activity_logs')


class Circles(Base):
    __tablename__ = 'circles'
    __table_args__ = (
        ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE', name='circles_ibfk_1'),
        Index('ix_circles_name', 'name'),
        Index('ix_circles_owner_id', 'owner_id'),
        Index('ix_circles_slug', 'slug'),
        Index('uq_circles_slug', 'slug', unique=True)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'private'"))
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))
    archived_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    owner: Mapped['Users'] = relationship('Users', back_populates='circles')
    circle_books: Mapped[list['CircleBooks']] = relationship('CircleBooks', back_populates='circle')
    circle_members: Mapped[list['CircleMembers']] = relationship('CircleMembers', back_populates='circle')
    circle_progress_updates: Mapped[list['CircleProgressUpdates']] = relationship('CircleProgressUpdates', back_populates='circle')


class LibraryItems(Base):
    __tablename__ = 'library_items'
    __table_args__ = (
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='library_items_ibfk_2'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='library_items_ibfk_1'),
        Index('book_id', 'book_id'),
        Index('ix_library_items_id', 'id'),
        Index('ix_library_items_status', 'status'),
        Index('uq_library_user_book', 'user_id', 'book_id', unique=True)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False)
    saved_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('(now())'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, server_default=text('(now())'))
    current_page: Mapped[Optional[int]] = mapped_column(Integer)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer)
    bookmark_page: Mapped[Optional[int]] = mapped_column(Integer)
    last_read_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    book: Mapped['Books'] = relationship('Books', back_populates='library_items')
    user: Mapped['Users'] = relationship('Users', back_populates='library_items')
    circle_progress_updates: Mapped[list['CircleProgressUpdates']] = relationship('CircleProgressUpdates', back_populates='library_item')


class UserConnections(Base):
    __tablename__ = 'user_connections'
    __table_args__ = (
        ForeignKeyConstraint(['addressee_id'], ['users.id'], ondelete='CASCADE', name='user_connections_ibfk_2'),
        ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE', name='user_connections_ibfk_1'),
        Index('ix_user_connections_addressee_id', 'addressee_id'),
        Index('ix_user_connections_requester_id', 'requester_id'),
        Index('ix_user_connections_status', 'status'),
        Index('uq_user_connection_pair', 'requester_id', 'addressee_id', unique=True)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(Integer, nullable=False)
    addressee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    relationship_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'friend'"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))

    addressee: Mapped['Users'] = relationship('Users', foreign_keys=[addressee_id], back_populates='user_connections_addressee')
    requester: Mapped['Users'] = relationship('Users', foreign_keys=[requester_id], back_populates='user_connections_requester')


class UserSettings(Base):
    __tablename__ = 'user_settings'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='user_settings_ibfk_1'),
        Index('ix_user_settings_id', 'id'),
        Index('user_id', 'user_id', unique=True)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    theme: Mapped[str] = mapped_column(String(20), nullable=False)
    density: Mapped[str] = mapped_column(String(20), nullable=False)
    reading_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    font_size: Mapped[str] = mapped_column(String(20), nullable=False)
    line_height: Mapped[str] = mapped_column(String(20), nullable=False)
    auto_bookmark: Mapped[int] = mapped_column(TINYINT(1), nullable=False)
    show_progress_bar: Mapped[int] = mapped_column(TINYINT(1), nullable=False)
    email_updates: Mapped[int] = mapped_column(TINYINT(1), nullable=False)
    reading_reminders: Mapped[int] = mapped_column(TINYINT(1), nullable=False)
    product_announcements: Mapped[int] = mapped_column(TINYINT(1), nullable=False)
    profile_visibility: Mapped[str] = mapped_column(String(20), nullable=False)
    share_reading_activity: Mapped[int] = mapped_column(TINYINT(1), nullable=False)
    onboarding_completed: Mapped[int] = mapped_column(TINYINT(1), nullable=False, server_default=text("'0'"))
    preferred_genres: Mapped[Optional[dict]] = mapped_column(JSON)
    reading_goals: Mapped[Optional[dict]] = mapped_column(JSON)
    content_styles: Mapped[Optional[dict]] = mapped_column(JSON)
    preferred_lengths: Mapped[Optional[dict]] = mapped_column(JSON)
    weekly_target: Mapped[Optional[str]] = mapped_column(String(80))

    user: Mapped['Users'] = relationship('Users', back_populates='user_settings')


class CircleBooks(Base):
    __tablename__ = 'circle_books'
    __table_args__ = (
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='circle_books_ibfk_2'),
        ForeignKeyConstraint(['circle_id'], ['circles.id'], ondelete='CASCADE', name='circle_books_ibfk_1'),
        ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE', name='circle_books_ibfk_3'),
        Index('created_by_user_id', 'created_by_user_id'),
        Index('ix_circle_books_book_id', 'book_id'),
        Index('ix_circle_books_circle_id', 'circle_id'),
        Index('ix_circle_books_status', 'status'),
        Index('uq_circle_book_pair', 'circle_id', 'book_id', unique=True)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circle_id: Mapped[int] = mapped_column(Integer, nullable=False)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    title_override: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    target_end_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))

    book: Mapped['Books'] = relationship('Books', back_populates='circle_books')
    circle: Mapped['Circles'] = relationship('Circles', back_populates='circle_books')
    created_by_user: Mapped['Users'] = relationship('Users', back_populates='circle_books')
    circle_progress_updates: Mapped[list['CircleProgressUpdates']] = relationship('CircleProgressUpdates', back_populates='circle_book')


class CircleMembers(Base):
    __tablename__ = 'circle_members'
    __table_args__ = (
        ForeignKeyConstraint(['circle_id'], ['circles.id'], ondelete='CASCADE', name='circle_members_ibfk_1'),
        ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], ondelete='SET NULL', name='circle_members_ibfk_3'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='circle_members_ibfk_2'),
        Index('invited_by_user_id', 'invited_by_user_id'),
        Index('ix_circle_members_circle_id', 'circle_id'),
        Index('ix_circle_members_user_id', 'user_id'),
        Index('uq_circle_member_pair', 'circle_id', 'user_id', unique=True)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circle_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'member'"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    invited_by_user_id: Mapped[Optional[int]] = mapped_column(Integer)
    joined_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))

    circle: Mapped['Circles'] = relationship('Circles', back_populates='circle_members')
    invited_by_user: Mapped[Optional['Users']] = relationship('Users', foreign_keys=[invited_by_user_id], back_populates='circle_members_invited_by_user')
    user: Mapped['Users'] = relationship('Users', foreign_keys=[user_id], back_populates='circle_members_user')


class CircleProgressUpdates(Base):
    __tablename__ = 'circle_progress_updates'
    __table_args__ = (
        ForeignKeyConstraint(['circle_book_id'], ['circle_books.id'], ondelete='CASCADE', name='circle_progress_updates_ibfk_2'),
        ForeignKeyConstraint(['circle_id'], ['circles.id'], ondelete='CASCADE', name='circle_progress_updates_ibfk_1'),
        ForeignKeyConstraint(['library_item_id'], ['library_items.id'], ondelete='SET NULL', name='circle_progress_updates_ibfk_4'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='circle_progress_updates_ibfk_3'),
        Index('ix_circle_progress_updates_circle_book_id', 'circle_book_id'),
        Index('ix_circle_progress_updates_circle_id', 'circle_id'),
        Index('ix_circle_progress_updates_created_at', 'created_at'),
        Index('ix_circle_progress_updates_user_id', 'user_id'),
        Index('library_item_id', 'library_item_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circle_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'circle'"))
    circle_book_id: Mapped[Optional[int]] = mapped_column(Integer)
    library_item_id: Mapped[Optional[int]] = mapped_column(Integer)
    current_page: Mapped[Optional[int]] = mapped_column(Integer)
    bookmark_page: Mapped[Optional[int]] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('(now())'))

    circle_book: Mapped[Optional['CircleBooks']] = relationship('CircleBooks', back_populates='circle_progress_updates')
    circle: Mapped['Circles'] = relationship('Circles', back_populates='circle_progress_updates')
    library_item: Mapped[Optional['LibraryItems']] = relationship('LibraryItems', back_populates='circle_progress_updates')
    user: Mapped['Users'] = relationship('Users', back_populates='circle_progress_updates')
