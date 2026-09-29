"""
AirChat Secure — Punto de entrada de la aplicación FastAPI.

Ensambla los routers, middleware y eventos de startup.
"""

import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import STATIC_DIR
from app.models.database import init_db
from app.services.ai_engine import init_llm
from app.routers import pages, metrics, chat


def create_app() -> FastAPI:
    """Factory de la aplicación FastAPI."""
    application = FastAPI(
        title="AirChat Secure",
        description="Chat privado con E2EE, IA local y RAG.",
        version="2.0.0",
    )

    # --- Middleware ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Static files ---
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # --- Routers ---
    application.include_router(pages.router)
    application.include_router(metrics.router)
    application.include_router(chat.router)

    # --- Startup ---
    @application.on_event("startup")
    async def on_startup():
        await init_db()
        asyncio.create_task(asyncio.to_thread(init_llm))

    return application


app = create_app()
