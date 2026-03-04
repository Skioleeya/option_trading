
import sys
import os
from pathlib import Path

# Add backend dir to path for imports
backend_dir = Path("e:/US.market/Option_v3/backend")
sys.path.append(str(backend_dir))

try:
    from app.config import settings
    from longport.openapi import Config, QuoteContext
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DIAG")

    token = settings.longport_access_token
    masked_token = f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "TOO SHORT"
    
    logger.info(f"Loaded APP_KEY: {settings.longport_app_key}")
    logger.info(f"Loaded TOKEN (masked): {masked_token}")
    logger.info(f"Token Length: {len(token)}")

    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    logger.info("Attempting QuoteContext connection...")
    ctx = QuoteContext(config)
    
    # Try a simple sync call to verify auth
    logger.info("Testing connection with member_id call (if available) or static info...")
    # LongPort SDK usually raises 401004 immediately if token is rejected on first network use
    # Let's try getting real-time quote for SPY
    from longport.openapi import SubType
    ctx.subscribe(["SPY.US"], [SubType.Quote])
    logger.info("Subscription request sent. If you see this, basic auth might be OK.")
    
except Exception as e:
    print(f"\n[DIAG ERROR] Connection Failed: {e}")
    if "401004" in str(e):
        print("Confirmed: Token is indeed rejected by LongPort Servers.")
    sys.exit(1)

print("\n[DIAG SUCCESS] Token accepted by QuoteContext initialization.")
