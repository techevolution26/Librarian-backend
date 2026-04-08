from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.storage import STORAGE_ROOT, ensure_storage_dirs
from app.routes import auth, books, library, profile, settings as settings_route

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

# Mount the root storage directory, not only books
# so these URLs work:
# /static/books/<file>
# /static/avatars/<file>
app.mount("/static", StaticFiles(directory=STORAGE_ROOT), name="static")

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(library.router)
app.include_router(profile.router)
app.include_router(settings_route.router)


@app.get("/")
def root():
    return {"message": "The Librarian API is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}