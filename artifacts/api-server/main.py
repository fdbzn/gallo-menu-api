"""Gallo — FastAPI backend service."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    perfiles,
    mesas,
    menus,
    amigos,
    platillos,
    ingredientes,
    listas,
    lugares,
    encuestas,
)

app = FastAPI(
    title="Gallo API",
    description="Backend colaborativo para planear menús en equipo.",
    version="1.0.0",
    root_path="/api",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(perfiles.router)
app.include_router(mesas.router)
app.include_router(menus.router)
app.include_router(amigos.router)
app.include_router(platillos.router)
app.include_router(ingredientes.router)
app.include_router(listas.router)
app.include_router(lugares.router)
app.include_router(encuestas.router)


@app.get("/healthz", tags=["health"])
async def health():
    return {"status": "ok"}
