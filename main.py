from __future__ import annotations
import os

# --- Hardware Optimization: Set thread limits before NumPy/SciPy imports ---
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"
# --------------------------------------------------------------------------

"""SPY 0DTE Dashboard — FastAPI Application.

Main entry point for the backend service.
Orchestrates all services via AppContainer with async lifespan management.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings

# Modular App Imports
from app.lifespan import lifespan
from app.routes import health, history, ws_dashboard

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI Application
# ============================================================================


app = FastAPI(
    title="SPY 0DTE Dashboard",
    description="Real-time SPY options GEX analysis dashboard",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(history.router)
app.include_router(ws_dashboard.router)
