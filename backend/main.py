from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers import (
    alerts,
    calculator,
    journal,
    market_stance,
    scanner,
    trades,
    watchlist,
)


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
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
