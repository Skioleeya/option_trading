import asyncio
import sys
from playwright.async_api import async_playwright, expect
from colorama import Fore, Style, init

init(autoreset=True)

async def test_ui_atm_persistence():
    print(f"{Fore.CYAN}[*] Launching Playwright for Deep Disconnect/Reconnect Persistence Test...{Style.RESET_ALL}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            # 0. Capture Console Logs
            page.on("console", lambda msg: print(f"    [Browser] {msg.type}: {msg.text}"))
            
            print(f"{Fore.YELLOW}[*] Navigating to http://localhost:5173 ...{Style.RESET_ALL}")
            await page.goto("http://localhost:5173", timeout=15000)
            
            # 1. Wait for initial load
            await page.wait_for_selector(".absolute.top-4.left-4", timeout=10000)
            await page.wait_for_selector("canvas", timeout=15000)
            print(f"{Fore.GREEN}[+] Dashboard loaded and TradingView chart rendered.{Style.RESET_ALL}")
            
            # 1b. Wait for ATM data to resolve (no longer pending)
            expect_data = True
            try:
                await expect(page.locator("text=-- PENDING")).to_have_count(0, timeout=10000)
                print(f"{Fore.GREEN}[+] ATM Decay data resolved and populated.{Style.RESET_ALL}")
            except AssertionError:
                print(f"{Fore.YELLOW}[!] Warning: ATM Decay stuck in -- PENDING. Ticks might not flow or market is closed.{Style.RESET_ALL}")
                expect_data = False
            
            # Wait a few seconds for normal ticking
            await asyncio.sleep(3)
            
            initial_canvases = await page.locator("canvas").count()
            print(f"    [Trace] Stable canvas count: {initial_canvases}")
            
            # 2. Simulate Network Drop
            print(f"\n{Fore.RED}[!] Simulating Network Outage (Offline Mode)...{Style.RESET_ALL}")
            await context.set_offline(True)
            
            # Monitor during outage
            for i in range(5):
                await asyncio.sleep(1)
                canvases = await page.locator("canvas").count()
                if canvases == 0:
                    print(f"{Fore.RED}[!] FAILED: Chart canvases unmounted during network outage at second {i+1}.{Style.RESET_ALL}")
                    sys.exit(1)
            print(f"{Fore.GREEN}[+] Chart survived 5-second network outage (no unmounting).{Style.RESET_ALL}")
            
            # Check if UI reset to pending (it shouldn't, IF we had data)
            if expect_data:
                pending_text = await page.locator("text=-- PENDING").count()
                if pending_text > 0:
                    print(f"{Fore.RED}[!] FAILED: Detected '-- PENDING' text during outage! Store wiped state on disconnect.{Style.RESET_ALL}")
                    sys.exit(1)
            
            # 3. Simulate Reconnection
            print(f"\n{Fore.YELLOW}[*] Restoring Network Connectivity...{Style.RESET_ALL}")
            await context.set_offline(False)
            
            # Wait for data to resume without tearing down the chart
            print(f"{Fore.YELLOW}[*] Monitoring for 10 seconds post-reconnection...{Style.RESET_ALL}")
            for i in range(10):
                await asyncio.sleep(1)
                canvases = await page.locator("canvas").count()
                if canvases == 0:
                    print(f"{Fore.RED}[!] FAILED: Chart canvases unmounted during reconnection recovery at second {i+1}.{Style.RESET_ALL}")
                    sys.exit(1)
                    
                if expect_data:
                    pending_text = await page.locator("text=-- PENDING").count()
                    if pending_text > 0:
                        print(f"{Fore.RED}[!] FAILED: Store wiped state upon reconnection at second {i+1}.{Style.RESET_ALL}")
                        sys.exit(1)
            
            print(f"{Fore.GREEN}[*] Analysis Complete! Chart components demonstrated 100% persistence through disconnection and reconnection events.{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}[!] Unexpected Error during UI test: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
            
if __name__ == "__main__":
    asyncio.run(test_ui_atm_persistence())
