"""
FastAPI アプリ。
- ローカル: uvicorn app.main:app --reload
- Lambda:  Mangum(app) でラップ
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api import ota, robots, schedules, telemetry

app = FastAPI(
    title="RobOps API",
    version="1.0.0",
    description="お掃除ロボット運用管理 API",
)

# CORS: ローカルは全許可、本番は CloudFront ドメインのみ
_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(robots.router)
app.include_router(telemetry.router)
app.include_router(schedules.router)
app.include_router(ota.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": os.getenv("ENV", "local")}


# ─── Lambda エントリポイント ─────────────────────────────
# ローカルと本番で同じコードが動く核心部分。
# uvicorn はこのモジュールの `app` を使い、
# Lambda は `handler` を使う。
handler = Mangum(app, lifespan="off")
