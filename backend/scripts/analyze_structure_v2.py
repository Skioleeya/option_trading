import sys
import os
import time
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple
from pathlib import Path
from zoneinfo import ZoneInfo

# 将后端根目录加入 path，以便能够直接导入 app.config 等模块
sys.path.append(str(Path(__file__).resolve().parents[1]))

from longport.openapi import QuoteContext, Config, CalcIndex
from app.config import settings

def print_header(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

async def fetch_chain_data(ctx: QuoteContext, symbol: str, exp_date: date, spot: float, limit_window: float = 100.0) -> Tuple[List[Dict], List[Dict]]:
    """
    拉取指定到期日的期权链基础信息，并通过 calc_indexes 获取 Volume 和 OI 数据。
    将 Call 和 Put 解耦分离。
    
    为避免触发 "Too many option securities request within one minute"，
    我们仅拉取 Spot 上下 limit_window 范围内的核心合约。
    """
    chain_info = ctx.option_chain_info_by_date(symbol, exp_date)
    if not chain_info:
        return [], []

    calls = []
    puts = []
    call_symbols = []
    put_symbols = []
    symbol_to_strike = {}

    for info in chain_info:
        strike = float(info.price) if hasattr(info, 'price') else 0.0
        # 核心过滤：剔除距离 spot 过远的极端虚值合约，以大幅降低 API 调用量
        if spot and abs(strike - spot) > limit_window:
            continue
            
        if hasattr(info, 'call_symbol') and info.call_symbol:
            call_symbols.append(info.call_symbol)
            symbol_to_strike[info.call_symbol] = strike
            calls.append({"symbol": info.call_symbol, "strike": strike, "type": "CALL", "vol": 0, "oi": 0})
        if hasattr(info, 'put_symbol') and info.put_symbol:
            put_symbols.append(info.put_symbol)
            symbol_to_strike[info.put_symbol] = strike
            puts.append({"symbol": info.put_symbol, "strike": strike, "type": "PUT", "vol": 0, "oi": 0})

    # 分批次调用 calc_indexes (避免超出单次配额)
    all_symbols = call_symbols + put_symbols
    batch_size = 50
    results = []
    
    print(f"    [Trace] 正在拉取 {len(all_symbols)} 个核心合约的 Volume/OI 数据...")
    for i in range(0, len(all_symbols), batch_size):
        batch = all_symbols[i:i + batch_size]
        try:
            res = ctx.calc_indexes(batch, [CalcIndex.Volume, CalcIndex.OpenInterest])
            results.extend(res)
            # 严格防范每分钟频控限制：大延迟 (单批次最多50，全脚本最多拉取 600-800 个)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [ERROR] calc_indexes 拉取失败: {e}")
            # 遇到频控时强制额外避让
            await asyncio.sleep(2.0)

    # 将数据映射回 calls, puts
    sym_data = {}
    for r in results:
        # LongPort SDK 可能将 volume 和 open_interest 设为空或0
        vol = int(r.volume) if hasattr(r, 'volume') and r.volume else 0
        oi = int(r.open_interest) if hasattr(r, 'open_interest') and r.open_interest else 0
        sym_data[r.symbol] = {"vol": vol, "oi": oi}

    for c in calls:
        if c["symbol"] in sym_data:
            c["vol"] = sym_data[c["symbol"]]["vol"]
            c["oi"] = sym_data[c["symbol"]]["oi"]
            
    for p in puts:
        if p["symbol"] in sym_data:
            p["vol"] = sym_data[p["symbol"]]["vol"]
            p["oi"] = sym_data[p["symbol"]]["oi"]

    # 过滤掉完全没数据的深度虚值（Volume=0 且 OI=0）以简化输出
    calls = [c for c in calls if c["vol"] > 0 or c["oi"] > 0]
    puts = [p for p in puts if p["vol"] > 0 or p["oi"] > 0]
    
    # 按照 strike 排序
    calls.sort(key=lambda x: x["strike"])
    puts.sort(key=lambda x: x["strike"])

    return calls, puts

def coverage_pct(data: List[Dict], spot: float, window: float, key: str) -> float:
    total = sum(d[key] for d in data)
    if total == 0: return 0.0
    covered = sum(d[key] for d in data if abs(d['strike'] - spot) <= window)
    return (covered / total) * 100

def get_top_n(data: List[Dict], key: str, n: int) -> List[Dict]:
    return sorted(data, key=lambda x: x[key], reverse=True)[:n]

def vwap_strike(data: List[Dict], key: str) -> float:
    total = sum(d[key] for d in data)
    if total == 0: return 0.0
    weighted_sum = sum(d['strike'] * d[key] for d in data)
    return weighted_sum / total

def format_node(d: Dict, spot: float, key: str, label: str) -> str:
    dist = d['strike'] - spot
    val = d[key]
    val_str = f"{val/10000:.1f}W" if val >= 10000 else str(val)
    return f"行权价 {d['strike']:<6} ({dist:+.1f}pt) | {label}: {val_str:<6}"

async def analyze():
    print_header("SPY 期权微观结构分析系统 v2.0 (Institution-Grade)")
    print(">>> 正在初始化 LongPort 核心上下文...")

    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token
    )
    ctx = QuoteContext(config)

    # 1. 获取现价
    spot_quotes = ctx.quote(["SPY.US"])
    if not spot_quotes:
        print("[Fatal] 无法获取 SPY 现价，程序终止。")
        return
    spot = float(spot_quotes[0].last_done)
    print(f"[*] 当前 SPY Spot = {spot:.2f}\n")

    # 2. 探查有效的 DTE (到期日)
    print(">>> 扫描即将到期的期权链矩阵...")
    base_date = datetime.now(ZoneInfo("US/Eastern")).date()
    valid_dates = []
    
    for i in range(14):
        check_date = base_date + timedelta(days=i)
        info = ctx.option_chain_info_by_date("SPY.US", check_date)
        if info and len(info) > 0:
            valid_dates.append(check_date)
            
    if not valid_dates:
        print("未找到任何期权数据，可能是非交易时间。")
        return

    dte_0 = valid_dates[0] if len(valid_dates) > 0 else None
    dte_1 = valid_dates[1] if len(valid_dates) > 1 else None
    dte_2 = valid_dates[2] if len(valid_dates) > 2 else None
    
    # Next Weekly: 第一遇到的周五（如果 0DTE, 1DTE, 2DTE 中有周五，则顺延找下一个）
    weekly_date = None
    for d in valid_dates[3:]:
        if d.weekday() == 4: # 4 is Friday
            weekly_date = d
            break

    print(f" [识别层级] 0DTE: {dte_0} | 1DTE: {dte_1} | 2DTE: {dte_2} | Weekly: {weekly_date}")

    # =========================================================
    # 0DTE 核心层分析 (末日冲击与 Gamma 核心区)
    # =========================================================
    if dte_0:
        print_header("【Layer 1】 0DTE 微观结构分析 (Gamma Scalping & 末日冲击)")
        calls, puts = await fetch_chain_data(ctx, "SPY.US", dte_0, spot, limit_window=100.0)
        
        c_vol25 = coverage_pct(calls, spot, 25, "vol")
        p_vol25 = coverage_pct(puts, spot, 25, "vol")
        
        print("\n[A] Volume (成交量) 分布验证：")
        print("逻辑基准: 0DTE 的日内投机极大集中于近端 ATM 附近 (±25pt)")
        print(f"  └─ Call ±25pt 内 Volume 占比: {c_vol25:.1f}%")
        print(f"  └─ Put  ±25pt 内 Volume 占比: {p_vol25:.1f}%")
        
        print("\n[B] OI (未平仓量) 极端引力墙 (Top 3 Nodes)：")
        print("逻辑基准: 远端缺乏流动性(低Vol)，但 OI 极大，形成真正的当日期权墙 (Gamma Wall)。")
        
        top3_c_oi = get_top_n(calls, "oi", 3)
        top3_p_oi = get_top_n(puts, "oi", 3)
        
        print("  🟢 Call 墙 (上方阻力)：")
        for node in top3_c_oi:
            print(f"     -> {format_node(node, spot, 'oi', 'OI')}")
            
        print("  🔴 Put  墙 (下方支撑)：")
        for node in top3_p_oi:
            print(f"     -> {format_node(node, spot, 'oi', 'OI')}")
            
        print("\n>> 架构启示: ±25pt 必须使用极速 WebSocket，而远端 Top Nodes 依赖 `calc_indexes` 轮询完全合理。")

    # =========================================================
    # 1DTE & 2DTE 展期与波段层 (Rollover 阵地)
    # =========================================================
    for dte, label in [(dte_1, "1DTE"), (dte_2, "2DTE")]:
        if not dte: continue
        print_header(f"【Layer 2】 {label} 微观结构分析 (Rollover与短线波段)")
        calls, puts = await fetch_chain_data(ctx, "SPY.US", dte, spot, limit_window=60.0)
        
        if not calls or not puts: continue
        
        c_vol_vwap = vwap_strike(calls, "vol")
        p_vol_vwap = vwap_strike(puts, "vol")
        c_oi_vwap = vwap_strike(calls, "oi")
        p_oi_vwap = vwap_strike(puts, "oi")
        
        c_vol20 = coverage_pct(calls, spot, 20, "vol")
        p_vol20 = coverage_pct(puts, spot, 20, "vol")

        print("\n[A] 增量博弈重力场 (Volume Weighted Average Strike)：")
        print("逻辑基准: Call 和 Put 的博弈重心由于 Skew 会发生错位，Put 的重心通常更低。")
        print(f"  └─ Call - 成交量重心: {c_vol_vwap:.2f} ({c_vol_vwap-spot:+.1f}pt) | OI重力心: {c_oi_vwap:.2f} ({c_oi_vwap-spot:+.1f}pt)")
        print(f"  └─ Put  - 成交量重心: {p_vol_vwap:.2f} ({p_vol_vwap-spot:+.1f}pt) | OI重力心: {p_oi_vwap:.2f} ({p_oi_vwap-spot:+.1f}pt)")

        print("\n[B] ±20pt 窗口覆盖率验证：")
        print(f"  └─ Call ±20pt Volume 占比: {c_vol20:.1f}%")
        print(f"  └─ Put  ±20pt Volume 占比: {p_vol20:.1f}%")
        
        print("\n>> 架构启示: 如果隔日 Put 覆盖率下降，说明跨日避险盘在买入远端 (ODT) 的深度 Put。我们需要适当放宽下方检测带。")

    # =========================================================
    # Next Weekly 结构主力博弈层 (Pinning Risks)
    # =========================================================
    if weekly_date:
        print_header("【Layer 3】 Next Weekly 微观结构分析 (月内趋势与结构锚点)")
        print("逻辑基准: Weekly 期权链的日内 Volume 噪音过大，真正主导市场路径的是累积起来的 OI 巨无霸。")
        calls, puts = await fetch_chain_data(ctx, "SPY.US", weekly_date, spot, limit_window=80.0)
        
        if calls and puts:
            top5_c_oi = get_top_n(calls, "oi", 5)
            top5_p_oi = get_top_n(puts, "oi", 5)
            
            print("\n[A] 核心引力节点 (Top 5 Call Nodes)：")
            for node in top5_c_oi:
                print(f"  🟢 {format_node(node, spot, 'oi', 'OI')}")
                
            print("\n[B] 核心支撑节点 (Top 5 Put Nodes)：")
            for node in top5_p_oi:
                print(f"  🔴 {format_node(node, spot, 'oi', 'OI')}")
                
            print("\n>> 架构启示: 这类节点通常离现价极远，实时推送的意义为 0。使用 `calc_indexes` 定时抓取其 Delta/Gamma 变动是唯一正解。")

    print("\n=================== 混合监测架构验证完成 ===================\n")

if __name__ == "__main__":
    try:
        asyncio.run(analyze())
    except KeyboardInterrupt:
        pass
