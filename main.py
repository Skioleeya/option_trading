from __future__ import annotations
import os

# --- Hyper-Early SDK Guard (Institutional Priority) ---
print("[PRE-FLIGHT] Initializing LongPort SDK C-Core...")
from longport.openapi import QuoteContext, Config
def _load_env_keys() -> None:
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

def _init_primary_ctx() -> QuoteContext | None:
    _load_env_keys()
    early_config = Config(
        app_key=os.environ.get("LONGPORT_APP_KEY", ""),
        app_secret=os.environ.get("LONGPORT_APP_SECRET", ""),
        access_token=os.environ.get("LONGPORT_ACCESS_TOKEN", ""),
    )
    # This MUST happen before CuPy/Numba/CUDA imports
    try:
        ctx = QuoteContext(early_config)
        print("[PRE-FLIGHT] SDK Primary Context READY.")
        return ctx
    except Exception as exc:
        print(
            "[PRE-FLIGHT] SDK Primary Context FAILED. "
            f"Entering degraded mode (primary_ctx=None). reason={exc}"
        )
        return None


PRIMARY_CTX = _init_primary_ctx()
# --------------------------------------------------

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
from app.container import build_container

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

# Attach primary context
app.state.primary_ctx = PRIMARY_CTX

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
