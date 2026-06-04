"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI

from app.api.middleware import install_middleware
from app.api.routes import config as config_routes
from app.api.routes import market as market_routes
from app.api.routes import portfolio as portfolio_routes
from app.api.routes import system as system_routes
from app.config import load_settings


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Load once and keep in app.state. The core already supports env overrides.
    settings = load_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="CriptoLab API", version="0.1.0", lifespan=_lifespan)
    install_middleware(app)

    api_prefix = "/api/v1"
    app.include_router(system_routes.router, prefix=api_prefix)
    app.include_router(config_routes.router, prefix=api_prefix)
    app.include_router(market_routes.router, prefix=api_prefix)
    app.include_router(portfolio_routes.router, prefix=api_prefix)

    # Sprint 2 routes
    from app.api.routes import alerts as alerts_routes
    from app.api.routes import backtest as backtest_routes
    from app.api.routes import decisions as decisions_routes
    from app.api.routes import prospecting as prospecting_routes
    from app.api.routes import risk as risk_routes

    app.include_router(risk_routes.router, prefix=api_prefix)
    app.include_router(backtest_routes.router, prefix=api_prefix)
    app.include_router(prospecting_routes.router, prefix=api_prefix)
    app.include_router(decisions_routes.router, prefix=api_prefix)
    app.include_router(alerts_routes.router, prefix=api_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, Any]:
        return {
            "status": "ok",
            "data": {"service": "criptolab-api", "api_base": "/api/v1"},
            "error": None,
            "meta": {},
        }

    @app.get("/api/v1/_debug/settings", include_in_schema=False)
    def debug_settings() -> dict[str, Any]:
        # Helpful in dev; not linked from docs.
        settings_dict = asdict(app.state.settings)
        return {"status": "ok", "data": settings_dict, "error": None, "meta": {}}

    return app
