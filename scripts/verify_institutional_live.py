import asyncio
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table
from l3_assembly.presenters.ui.active_options.presenter import ActiveOptionsPresenter
from l0_ingest.feeds.option_chain_builder import OptionChainBuilder
from shared.config import settings

# Configure logging to focus on institutional metrics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InstitutionalVerifier")

console = Console()

async def verify_institutional_flow():
    """Live verification of OFII and Sweep detection."""
    console.print("[bold cyan]Starting Institutional Metric Verification (v4.0)...[/bold cyan]")
    
    # 1. Initialize core components
    builder = OptionChainBuilder()
    await builder.initialize()
    presenter = ActiveOptionsPresenter()
    
    console.print(f"[*] Monitoring configuration: Multiplier={settings.flow_sweep_multiplier}, Depth={settings.flow_market_depth_baseline}")

    try:
        while True:
            # 2. Get latest enriched snapshot from L0/L1
            # Note: This simulates a live tick cycle
            snapshot = await builder.fetch_chain()
            if not snapshot or not snapshot.get("chain"):
                console.print("[yellow]Waiting for live data feed...[/yellow]")
                await asyncio.sleep(2)
                continue
            
            # 3. Process through L3 Presenter (recalculates OFII/Sweeps)
            await presenter.update_background(
                chain=snapshot["chain"],
                spot=snapshot["spot"],
                atm_iv=snapshot["aggregate_greeks"].get("atm_iv", 0.0),
                gex_regime="NEUTRAL", # Default
                ttm_seconds=snapshot.get("ttm_seconds"),
                limit=10
            )
            
            # 4. Extract and Display Results
            latest = presenter.get_latest()
            
            table = Table(title=f"Institutional Flow Monitor - {datetime.now().strftime('%H:%M:%S')}")
            table.add_column("#", justify="center")
            table.add_column("SYM", style="cyan")
            table.add_column("STRIKE", justify="right")
            table.add_column("IMPACT (OFII)", style="bold yellow", justify="right")
            table.add_column("SWEEP", justify="center")
            table.add_column("FLOW", justify="right")
            table.add_column("VOL", justify="right")

            for i, opt in enumerate(latest):
                is_sweep = opt.get("is_sweep", False)
                sweep_marker = "[bold pulse white]SWEEP[/bold pulse white]" if is_sweep else "—"
                impact = f"{opt.get('impact_index', 0.0):.2f}"
                
                table.add_row(
                    str(i+1),
                    f"{opt['option_type'][0]}@{opt['symbol'][-8:]}",
                    f"{opt['strike']:.1f}",
                    impact,
                    sweep_marker,
                    opt.get("flow_deg_formatted", "$0"),
                    str(opt['volume'])
                )
            
            console.clear()
            console.print(table)
            console.print(f"\n[dim]Peak Impact captured in Reactor: {snapshot.get('aggregate_greeks', {}).get('max_impact', 0.0):.0f}[/dim]")
            
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[bold red]Verification stopped by user.[/bold red]")
    except Exception as e:
        logger.exception("Verification loop failed")

if __name__ == "__main__":
    asyncio.run(verify_institutional_flow())
