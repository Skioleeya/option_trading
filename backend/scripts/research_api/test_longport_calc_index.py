import asyncio
import logging
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from longport.openapi import QuoteContext, Config, CalcIndex
from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_calc_index")

async def test_calc_index(ctx: QuoteContext, symbols: list[str]):
    logger.info(f"--- Testing CalcIndex for {symbols} ---")
    
    # Explicitly requesting common and option-specific indicators from docs
    # Correcting based on error feedback (e.g. ChangeVal -> ChangeValue)
    indexes = [
        CalcIndex.LastDone, CalcIndex.ChangeValue, CalcIndex.ChangeRate,
        CalcIndex.Volume, CalcIndex.Turnover, CalcIndex.TurnoverRate,
        CalcIndex.TotalMarketValue, CalcIndex.CapitalFlow, CalcIndex.Amplitude,
        CalcIndex.PeTtmRatio, CalcIndex.PbRatio, CalcIndex.DividendRatioTtm,
        CalcIndex.FiveDayChangeRate, CalcIndex.TenDayChangeRate, 
        CalcIndex.HalfYearChangeRate, CalcIndex.FiveMinutesChangeRate,
        CalcIndex.ExpiryDate, CalcIndex.StrikePrice, CalcIndex.UpperStrikePrice,
        CalcIndex.LowerStrikePrice, CalcIndex.OutstandingQty, CalcIndex.OutstandingRatio,
        CalcIndex.Premium, CalcIndex.ItmOtm, CalcIndex.ImpliedVolatility,
        CalcIndex.WarrantDelta, CalcIndex.CallPrice, CalcIndex.ToCallPrice,
        CalcIndex.EffectiveLeverage, CalcIndex.LeverageRatio, CalcIndex.ConversionRatio,
        CalcIndex.BalancePoint, CalcIndex.OpenInterest, CalcIndex.Delta,
        CalcIndex.Gamma, CalcIndex.Theta, CalcIndex.Vega, CalcIndex.Rho
    ]
    
    try:
        results = ctx.calc_indexes(symbols, indexes)
        if results:
            for res in results:
                logger.info(f"[SUCCESS] CalcIndex for {res.symbol}:")
                # Common fields
                logger.info(f"  Last Done: {res.last_done}, Change Rate: {res.change_rate}%")
                logger.info(f"  Amplitude: {res.amplitude}, Volume Ratio: {res.volume_ratio}")
                
                # Equity specific (potentially)
                if res.total_market_value:
                    logger.info(f"  Market Value: {res.total_market_value}")
                
                # Option specific
                if res.expiry_date:
                    logger.info(f"  Expiry: {res.expiry_date}, Strike: {res.strike_price}")
                    logger.info(f"  ITM/OTM: {res.itm_otm}, IV: {res.implied_volatility}")
                    logger.info(f"  Greeks: Delta={res.delta}, Gamma={res.gamma}, Theta={res.theta}")
        else:
            logger.warning(f"[EMPTY] CalcIndex returned nothing for {symbols}")
    except Exception as e:
        logger.error(f"[ERROR] CalcIndex failed: {e}")

async def run_test():
    try:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)

        # 1. Identify target symbols (SPY + some options)
        spot_sym = "SPY.US"
        
        # Get options for today (0DTE)
        today = datetime.now(ZoneInfo("US/Eastern")).date()
        chains = ctx.option_chain_info_by_date(spot_sym, today)
        
        if not chains:
            logger.error("No option chains found for today.")
            return

        # Select 1 ATM Call
        quotes = ctx.quote([spot_sym])
        spot_price = float(quotes[0].last_done)
        closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot_price))
        atm_chain = [c for c in chains if float(c.price) == closest_strike][0]
        call_sym = atm_chain.call_symbol

        # Run tests
        await test_calc_index(ctx, [spot_sym, call_sym])

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
