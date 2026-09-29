"""Rutas HTTP para servir páginas."""

import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.config import TEMPLATES_DIR

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index():
    """Sirve la página principal del chat."""
    path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
