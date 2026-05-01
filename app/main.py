import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.storage import ensure_storage_dirs
from app.routes import auth, books, library, profile, settings as settings_route, connections, circles
from app.core.database import Base, engine

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_storage_dirs()

# Resolved the AssertionError by using pathlib.Path instead of fastapi.Path
STORAGE_ROOT = Path(os.getenv("STORAGE_DIR", "./storage"))
BOOK_STORAGE_DIR = STORAGE_ROOT / "books"
AVATAR_STORAGE_DIR = STORAGE_ROOT / "avatars"

# Ensure directories exist
BOOK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
AVATAR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static/books", StaticFiles(directory=BOOK_STORAGE_DIR), name="book-files")
app.mount("/static/avatars", StaticFiles(directory=AVATAR_STORAGE_DIR), name="avatar-files")

# Include Routers
app.include_router(auth.router)
app.include_router(books.router)
app.include_router(library.router)
app.include_router(profile.router)
app.include_router(settings_route.router)
app.include_router(connections.router)
app.include_router(circles.router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "The Librarian API is running!"}

@app.get("/health")
def health():
    return {"status": "ok"}
