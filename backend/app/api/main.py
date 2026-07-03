from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.routes import router as public_router
from app.db import ensure_schema


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Bootstrap idempotente; los cambios de esquema posteriores van por Alembic
    await ensure_schema()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="PokePrecio API",
    description="Comparador de precios de productos Pokémon TCG en tiendas chilenas",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["192.168.1.100:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
