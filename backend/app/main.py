"""FastAPI エントリポイント。"""

from __future__ import annotations

import contextlib
import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from app.db import init_db
from app.routers import auth, consent, ebpm, myna_oauth, offline, philsys_oauth, products, programs, purchase, seed, treasury, wallet


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
app.include_router(consent.router)
app.include_router(myna_oauth.router)
app.include_router(philsys_oauth.router)
app.include_router(programs.router)
app.include_router(wallet.router)
app.include_router(products.router)
app.include_router(purchase.router)
app.include_router(ebpm.router)
app.include_router(offline.router)
app.include_router(treasury.router)
app.include_router(seed.router)

# 静的フロントエンド
# - 開発中はブラウザに HTML/JS/CSS をキャッシュさせない (新 UI が見えない問題を防止)
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


FRONTEND_DIR = pathlib.Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", NoCacheStaticFiles(directory=FRONTEND_DIR, html=True), name="ui")


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
