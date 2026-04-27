"""FastAPI エントリポイント。"""

from __future__ import annotations

import contextlib
import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import auth, ebpm, products, programs, purchase, seed, wallet


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="JPN PBM",
    description="東京都ステーブルコイン助成金 PBM MVP",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(programs.router)
app.include_router(wallet.router)
app.include_router(products.router)
app.include_router(purchase.router)
app.include_router(ebpm.router)
app.include_router(seed.router)

# 静的フロントエンド
FRONTEND_DIR = pathlib.Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/index.html", status_code=307)


@app.get("/api", include_in_schema=False)
def api_meta():
    return {
        "name": "JPN PBM",
        "ui": [
            "/ui/tokyo.html",
            "/ui/citizen.html",
            "/ui/retailer.html",
            "/ui/ebpm.html",
        ],
        "docs": "/docs",
    }
