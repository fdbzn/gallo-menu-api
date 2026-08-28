"""Gallo — FastAPI backend service."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import PostgRESTError
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
    segmentos_menu,
    siguiente_compra,
    cuenta_confirmada,
    reset_password,
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
app.include_router(cuenta_confirmada.router)
app.include_router(reset_password.router)
app.include_router(perfiles.router)
app.include_router(mesas.router)
app.include_router(mesas.compartir_router)
app.include_router(menus.router)
app.include_router(amigos.router)
app.include_router(platillos.router)
app.include_router(ingredientes.router)
app.include_router(ingredientes.cat_router)
app.include_router(listas.router)
app.include_router(lugares.router)
app.include_router(lugares.rpc_router)
app.include_router(encuestas.router)
app.include_router(segmentos_menu.router)
app.include_router(siguiente_compra.router)


@app.exception_handler(PostgRESTError)
async def postgrest_error_handler(_request, exc: PostgRESTError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/healthz", tags=["health"])
async def health():
    return {"status": "ok"}
