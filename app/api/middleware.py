"""API middleware (CORS, error handlers)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

def install_middleware(app: FastAPI) -> None:
    # In dev, Next.js will typically proxy via rewrites.
    # This permissive CORS is still useful for local testing.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "data": None,
                "error": {"message": str(exc), "type": exc.__class__.__name__},
                "meta": {},
            },
        )
