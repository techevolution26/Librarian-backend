from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes import books, library, profile, settings as settings_route

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_dir =Path("storage")
storage_dir.mkdir(parents=True,exist_ok=True)

app.mount("/static", StaticFiles(directory=storage_dir), name="static")
app.mount("/static/avatars", StaticFiles(directory=storage_dir / "avatars"), name="avatars")


app.include_router(books.router)
app.include_router(library.router)
app.include_router(profile.router)
app.include_router(settings_route.router)

@app.get("/")
def health():
    return {"message": "The Librarian API is running!"}