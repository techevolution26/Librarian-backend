from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.storage import COVERS_STORAGE_DIR, ensure_storage_dirs
from app.routes import archival_objects
from app.routes import iiif, auth, books, library, profile, settings as settings_route, connections, circles, notifications, collections, preservation_events, fixity, bookmarks, notebook
from app.core.database import Base, engine
from sqlalchemy import text

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    description=(
        "API for The Librarian — a community reading archive. Serves the web "
        "app and, on the same endpoints/auth, the Expo mobile app."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Login, session, and current-user endpoints."},
        {"name": "books", "description": "Public catalog, discovery/facets, admin catalog management."},
        {"name": "collections", "description": "Curated archival collections and their public catalogue boundary."},
        {"name": "library", "description": "A user's personal shelf and reading progress."},
        {"name": "circles", "description": "Shared reading groups."},
        {"name": "connections", "description": "Following/friending between users."},
        {"name": "profile", "description": "The current user's profile."},
        {"name": "settings", "description": "The current user's app settings."},
        {"name": "notifications", "description": "Realtime and persisted in-app notifications."},
        {"name": "preservation", "description": "Append-only archival preservation history."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_storage_dirs()

# Resolved the AssertionError by using pathlib.Path instead of fastapi.Path
STORAGE_ROOT = Path(settings.storage_dir).expanduser().resolve()
STATIC_ASSET_DIR = Path(__file__).resolve().parent / "static"
BOOK_STORAGE_DIR = STORAGE_ROOT / "books"
AVATAR_STORAGE_DIR = STORAGE_ROOT / "avatars"

# Ensure directories exist
BOOK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
AVATAR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
COVERS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static/books", StaticFiles(directory=BOOK_STORAGE_DIR), name="book-files")
app.mount("/static/avatars", StaticFiles(directory=AVATAR_STORAGE_DIR), name="avatar-files")
app.mount("/static/covers", StaticFiles(directory=COVERS_STORAGE_DIR), name="cover-files")
app.mount("/static/assets", StaticFiles(directory=STATIC_ASSET_DIR), name="static-assets")

# Include Routers
app.include_router(auth.router)
app.include_router(books.router)
app.include_router(library.router)
app.include_router(profile.router)
app.include_router(settings_route.router)
app.include_router(connections.router)
app.include_router(circles.router)
app.include_router(notifications.router)
app.include_router(collections.router)
app.include_router(archival_objects.router)
app.include_router(iiif.router)
app.include_router(preservation_events.router)
app.include_router(fixity.router)
app.include_router(bookmarks.router)
app.include_router(notebook.router)

# @app.on_event("startup")
# def startup():
#     Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "The Librarian API is running!"}

@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc

    return {"status": "ok"}
