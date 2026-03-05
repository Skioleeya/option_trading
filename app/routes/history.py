"""Historical data endpoints."""

from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/history")
async def get_history(request: Request, count: int = 50):
    """Retrieve historical snapshots from Redis."""
    container = request.app.state.container
    if container.l3_reactor:
        history = await container.l3_reactor.store.get_warm_latest(count)
    else:
        history = await container.historical_store.get_latest(count)
    return {"history": history, "count": len(history)}


@router.get("/api/atm-decay/history")
async def get_atm_decay_history(request: Request):
    """Retrieve the full historical ATM decay series for the current trade date."""
    container = request.app.state.container
    date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
    history = await container.atm_decay_tracker.get_history(date_str)
    
    return {
        "date": date_str,
        "history": history,
        "count": len(history)
    }

@router.post("/api/atm-decay/flush-history")
async def flush_atm_decay_history(request: Request):
    """Flush and rebuild the ATM decay history from the Intraday API."""
    container = request.app.state.container
    date_str = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
    await container.atm_decay_tracker.flush_and_rebuild()
    history = await container.atm_decay_tracker.get_history(date_str)
    
    return {
        "date": date_str,
        "message": "History flushed and rebuilt",
        "history": history,
        "count": len(history)
    }
