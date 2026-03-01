import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
from backend.routers import (
    alerts,
    calculator,
    journal,
    market_stance,
    scanner,
    trades,
    watchlist,
)
from backend.routers.alerts_app import router as alerts_app_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="Champion Trader System",
    description="Swing trading intelligence platform based on Afzal Lokhandwala's Champion Trader methodology",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend to connect
# In production on Railway, frontend domain varies; allow all origins
# since this is a private trading tool, not a public API
_origins = [origin.strip() for origin in settings.allowed_origins.split(",")]
if settings.environment == "production" or "*" in _origins:
    _origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False if "*" in _origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(scanner.router)
app.include_router(watchlist.router)
app.include_router(calculator.router)
app.include_router(trades.router)
app.include_router(journal.router)
app.include_router(market_stance.router)
app.include_router(alerts.router)
app.include_router(alerts_app_router)


@app.get("/")
def root():
    return {
        "name": "Champion Trader System",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
