import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        print("Navigating to http://localhost:5173/ ...")
        await page.goto("http://localhost:5173/")
        
        print("Waiting for page load and mockL4 injection...")
        await page.wait_for_timeout(3000)
        
        payloads = [
            {
                "type": "dashboard_update",
                "timestamp": "2026-03-04T09:30:00",
                "heartbeat_timestamp": "2026-03-04T09:30:00",
                "version": 100,
                "spot": 560.0,
                "agent_g": {
                    "data": {
                        "fused": { "direction": "BULLISH", "confidence": 0.85, "summary": "Mock signal: BULLISH" },
                        "ui_state": {
                            "micro_stats": {
                                "net_gex": { "label": "420B", "badge": "badge-positive" },
                                "wall_dyn": { "label": "Bullish", "badge": "badge-positive" },
                                "vanna": { "label": "-12.5", "badge": "badge-negative" },
                                "momentum": { "label": "Rising", "badge": "badge-positive" }
                            },
                            "tactical_triad": { "alignment": 1.0, "vrp": -12.0, "gamma_accel": 0.8 },
                            "wall_migration": [
                                { "strike": 550.0, "type": "Put Wall", "is_breached": False },
                                { "strike": 570.0, "type": "Call Wall", "is_breached": False }
                            ],
                            "mtf_flow": { "consensus": "BULLISH", "strength": 0.9 },
                            "depth_profile": [],
                            "active_options": [],
                            "skew_dynamics": {},
                            "macro_volume_map": {}
                        }
                    }
                }
            },
            {
                "type": "dashboard_update",
                "timestamp": "2026-03-04T09:30:01",
                "heartbeat_timestamp": "2026-03-04T09:30:01",
                "version": 100,
                "spot": 561.2,
                "agent_g": {
                    "data": {
                        "fused": { "direction": "BULLISH", "confidence": 0.85, "summary": "Mock signal: BULLISH" },
                        "ui_state": {
                         "micro_stats": {
                                "net_gex": { "label": "420B", "badge": "badge-positive" },
                                "wall_dyn": { "label": "Bullish", "badge": "badge-positive" },
                                "vanna": { "label": "-12.5", "badge": "badge-negative" },
                                "momentum": { "label": "Rising", "badge": "badge-positive" }
                            },
                            "tactical_triad": { "alignment": 1.0, "vrp": -12.0, "gamma_accel": 0.8 },
                            "wall_migration": [
                                { "strike": 550.0, "type": "Put Wall", "is_breached": False },
                                { "strike": 570.0, "type": "Call Wall", "is_breached": False }
                            ],
                            "mtf_flow": { "consensus": "BULLISH", "strength": 0.9 },
                            "depth_profile": [],
                            "active_options": [],
                            "skew_dynamics": {},
                            "macro_volume_map": {}
                        }
                    }
                }
            },
            {
                "type": "dashboard_update",
                "timestamp": "2026-03-04T09:30:02",
                "heartbeat_timestamp": "2026-03-04T09:30:02",
                "version": 100,
                "spot": 561.2,
                "agent_g": {
                    "data": {
                        "fused": { "direction": "BULLISH", "confidence": 0.85, "summary": "Mock signal: BULLISH" },
                        "ui_state": {
                         "micro_stats": {
                                "net_gex": { "label": "420B", "badge": "badge-positive" },
                                "wall_dyn": { "label": "Bullish", "badge": "badge-positive" },
                                "vanna": { "label": "-12.5", "badge": "badge-negative" },
                                "momentum": { "label": "Rising", "badge": "badge-positive" }
                            },
                            "tactical_triad": { "alignment": 1.0, "vrp": -12.0, "gamma_accel": 0.8 },
                            "wall_migration": [
                                { "strike": 550.0, "type": "Put Wall", "is_breached": False },
                                { "strike": 570.0, "type": "Call Wall", "is_breached": False }
                            ],
                            "mtf_flow": { "consensus": "BULLISH", "strength": 0.9 },
                            "depth_profile": [],
                            "active_options": [],
                            "skew_dynamics": {},
                            "macro_volume_map": {}
                        }
                    }
                }
            },
            {
                "type": "dashboard_update",
                "timestamp": "2026-03-04T09:30:03",
                "heartbeat_timestamp": "2026-03-04T09:30:03",
                "version": 100,
                "spot": 562.0,
                "agent_g": {
                    "data": {
                        "fused": { "direction": "BEARISH", "confidence": 0.85, "summary": "Mock signal: BEARISH" },
                        "ui_state": {
                         "micro_stats": {
                                "net_gex": { "label": "420B", "badge": "badge-positive" },
                                "wall_dyn": { "label": "Wait", "badge": "badge-neutral" },
                                "vanna": { "label": "-12.5", "badge": "badge-negative" },
                                "momentum": { "label": "Falling", "badge": "badge-negative" }
                            },
                            "tactical_triad": { "alignment": -1.0, "vrp": -12.0, "gamma_accel": -0.8 },
                            "wall_migration": [
                                { "strike": 550.0, "type": "Put Wall", "is_breached": False },
                                { "strike": 570.0, "type": "Call Wall", "is_breached": False }
                            ],
                            "mtf_flow": { "consensus": "BEARISH", "strength": 0.9 },
                            "depth_profile": [],
                            "active_options": [],
                            "skew_dynamics": {},
                            "macro_volume_map": {}
                        }
                    }
                }
            }
        ]
        
        for i, payload in enumerate(payloads):
            print(f"Injecting payload {i} (Spot: {payload['spot']})...")
            # Execute injection
            js_code = f"if (window.mockL4) {{ window.mockL4.injectPayload({json.dumps(payload)}); }} else {{ console.error('No mockL4!'); }}"
            await page.evaluate(js_code)
            
            # Wait for React to render
            await page.wait_for_timeout(1000)
            
            # Take screenshot
            save_path = f"e:/US.market/Option_v3/l4_frontend/screenshot_payload_{i}.png"
            await page.screenshot(path=save_path)
            print(f"Saved {save_path}")
            
            # Give it an extra second before next payload to simulate time passing
            await page.wait_for_timeout(1000)
            
        print("Simulation complete.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
    
