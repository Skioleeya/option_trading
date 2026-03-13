import math
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import numpy as np
import pandas as pd


# NOTE:
# This file is an external inventory-reconstruction example. It is not the
# repository's canonical Longbridge-backed GEX implementation. The live system
# currently uses OI-based proxy semantics because the public Longbridge feed
# does not expose customer/dealer, open-close, or aggressor-side labels.


# =========================
# 1) Black-Scholes gamma
# =========================

def norm_pdf(x: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * x * x) / np.sqrt(2.0 * np.pi)


def bs_gamma(
    spot: np.ndarray,
    strike: np.ndarray,
    ttm: np.ndarray,
    vol: np.ndarray,
    rate: np.ndarray,
    div: np.ndarray
) -> np.ndarray:
    """
    Black-Scholes unit gamma.
    Returns gamma per 1 share / 1 underlying unit.
    """
    spot = np.asarray(spot, dtype=float)
    strike = np.asarray(strike, dtype=float)
    ttm = np.asarray(ttm, dtype=float)
    vol = np.asarray(vol, dtype=float)
    rate = np.asarray(rate, dtype=float)
    div = np.asarray(div, dtype=float)

    # 数值稳定处理
    eps = 1e-12
    ttm = np.maximum(ttm, eps)
    vol = np.maximum(vol, eps)
    spot = np.maximum(spot, eps)
    strike = np.maximum(strike, eps)

    sqrt_t = np.sqrt(ttm)
    d1 = (
        np.log(spot / strike) +
        (rate - div + 0.5 * vol * vol) * ttm
    ) / (vol * sqrt_t)

    gamma = np.exp(-div * ttm) * norm_pdf(d1) / (spot * vol * sqrt_t)
    return gamma


# =========================
# 2) 数据结构与预处理
# =========================

@dataclass
class ModelConfig:
    contract_multiplier: int = 100
    gex_scale_per_1pct: bool = True
    # 如果 True，则输出的是“每 1% 标的变化导致的 delta notional 变化”
    # 即常见的 gamma dollar exposure 表示法：gamma * position * S^2 * 0.01
    # 如果 False，则输出 gamma * position * S


def prepare_option_frame(options: pd.DataFrame) -> pd.DataFrame:
    """
    期权静态表，至少应包含：
    - option_id
    - option_type: 'C' / 'P'
    - strike
    - expiry
    - iv
    - rate
    - div
    """
    df = options.copy()

    required = ["option_id", "option_type", "strike", "expiry", "iv"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"options 缺少必要字段: {missing}")

    df["option_type"] = df["option_type"].str.upper()
    if "rate" not in df.columns:
        df["rate"] = 0.0
    if "div" not in df.columns:
        df["div"] = 0.0

    return df


def prepare_trade_frame(trades: pd.DataFrame) -> pd.DataFrame:
    """
    成交流表，至少应包含：
    - option_id
    - timestamp
    - qty                  # 成交张数
    - side                 # 'buy' / 'sell'，相对“客户主动方向”
    - opening_flag         # +1 开仓, -1 平仓, 0 未知
    可选：
    - customer_type        # 'customer', 'firm', 'mm'...
    - aggressor            # 'buyer' / 'seller'
    """
    df = trades.copy()

    required = ["option_id", "timestamp", "qty", "side", "opening_flag"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"trades 缺少必要字段: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["side"] = df["side"].str.lower()
    df["qty"] = df["qty"].astype(float)
    df["opening_flag"] = df["opening_flag"].astype(float)

    return df


# =========================
# 3) 机构近似：重建 dealer inventory
# =========================

def infer_dealer_signed_position_from_trades(
    trades: pd.DataFrame,
    customer_only: bool = True
) -> pd.DataFrame:
    """
    根据成交流重建 dealer signed position。
    返回按 option_id 聚合后的：
    - dealer_pos_contracts

    符号约定：
    - customer 买入开仓 -> dealer 卖出 -> dealer position 为负
    - customer 卖出开仓 -> dealer 买入 -> dealer position 为正
    - customer 买入平仓 -> customer 减少多头 -> dealer 回补空头 -> dealer position 增加
    - customer 卖出平仓 -> customer 减少空头 -> dealer 减少多头 -> dealer position 减少

    一个统一写法：
        customer_position_change = side_sign * opening_flag * qty
    其中:
        side_sign = +1 (customer buy), -1 (customer sell)

        dealer_position_change = - customer_position_change
    """
    df = trades.copy()

    if customer_only and "customer_type" in df.columns:
        df = df[df["customer_type"].str.lower().eq("customer")].copy()

    side_map = {"buy": 1.0, "sell": -1.0}
    if not set(df["side"].unique()).issubset(set(side_map.keys())):
        bad = sorted(set(df["side"].unique()) - set(side_map.keys()))
        raise ValueError(f"side 存在非法值: {bad}")

    df["side_sign"] = df["side"].map(side_map)
    df["customer_pos_change"] = df["side_sign"] * df["opening_flag"] * df["qty"]
    df["dealer_pos_change"] = -df["customer_pos_change"]

    dealer_pos = (
        df.groupby("option_id", as_index=False)["dealer_pos_change"]
        .sum()
        .rename(columns={"dealer_pos_change": "dealer_pos_contracts"})
    )

    return dealer_pos


def merge_inventory(
    options: pd.DataFrame,
    dealer_pos: pd.DataFrame,
    fallback_open_interest: Optional[pd.DataFrame] = None,
    oi_sign_rule: str = "classic"
) -> pd.DataFrame:
    """
    把 dealer inventory 合并到静态期权表。

    fallback_open_interest 可包含：
    - option_id
    - open_interest

    当某些合约没有成交流重建值时，用 OI 近似补全：
    classic:
      call -> dealer short => negative
      put  -> dealer long  => positive
    注意：这是近似，不是真实库存。
    """
    df = options.copy()
    df = df.merge(dealer_pos, on="option_id", how="left")

    if fallback_open_interest is not None:
        oi = fallback_open_interest.copy()
        if "option_id" not in oi.columns or "open_interest" not in oi.columns:
            raise ValueError("fallback_open_interest 需包含 option_id, open_interest")
        df = df.merge(oi[["option_id", "open_interest"]], on="option_id", how="left")
    else:
        df["open_interest"] = np.nan

    if oi_sign_rule != "classic":
        raise ValueError("目前仅支持 oi_sign_rule='classic'")

    missing_mask = df["dealer_pos_contracts"].isna()
    if missing_mask.any():
        # classic heuristic:
        # call: dealer short -> negative
        # put:  dealer long  -> positive
        fallback_sign = np.where(df["option_type"].eq("C"), -1.0, 1.0)
        fallback_pos = fallback_sign * df["open_interest"].fillna(0.0)
        df.loc[missing_mask, "dealer_pos_contracts"] = fallback_pos[missing_mask]

    df["dealer_pos_contracts"] = df["dealer_pos_contracts"].fillna(0.0)
    return df


# =========================
# 4) 计算某个时点/spot 下的 GEX
# =========================

def add_time_to_maturity(
    df: pd.DataFrame,
    valuation_ts: pd.Timestamp
) -> pd.DataFrame:
    out = df.copy()
    valuation_ts = pd.Timestamp(valuation_ts)

    expiry_ts = pd.to_datetime(out["expiry"])
    ttm_days = (expiry_ts - valuation_ts).dt.total_seconds() / (365.0 * 24 * 3600)
    out["ttm"] = np.maximum(ttm_days, 1e-8)
    return out


def compute_gex_at_spot(
    inventory_df: pd.DataFrame,
    spot: float,
    valuation_ts: pd.Timestamp,
    config: ModelConfig = ModelConfig()
) -> pd.DataFrame:
    """
    对每个期权在给定 spot 下重算 gamma 和 GEX。
    返回逐合约明细。
    """
    df = add_time_to_maturity(inventory_df, valuation_ts)

    n = len(df)
    spot_arr = np.full(n, float(spot))
    strike_arr = df["strike"].to_numpy(dtype=float)
    ttm_arr = df["ttm"].to_numpy(dtype=float)
    vol_arr = df["iv"].to_numpy(dtype=float)
    rate_arr = df["rate"].to_numpy(dtype=float)
    div_arr = df["div"].to_numpy(dtype=float)

    gamma = bs_gamma(
        spot=spot_arr,
        strike=strike_arr,
        ttm=ttm_arr,
        vol=vol_arr,
        rate=rate_arr,
        div=div_arr
    )

    df["gamma_unit"] = gamma

    # dealer signed shares equivalent
    df["dealer_pos_shares"] = df["dealer_pos_contracts"] * config.contract_multiplier

    if config.gex_scale_per_1pct:
        # 常见机构/数据商口径：
        # gamma * signed_position * S^2 * 0.01
        df["gex"] = df["gamma_unit"] * df["dealer_pos_shares"] * (spot ** 2) * 0.01
    else:
        # 更原始的 delta-sensitivity notional 近似
        df["gex"] = df["gamma_unit"] * df["dealer_pos_shares"] * spot

    return df


def aggregate_gex_by_strike(gex_df: pd.DataFrame) -> pd.DataFrame:
    out = (
        gex_df.groupby(["strike", "option_type"], as_index=False)["gex"]
        .sum()
        .pivot(index="strike", columns="option_type", values="gex")
        .fillna(0.0)
        .reset_index()
    )

    if "C" not in out.columns:
        out["C"] = 0.0
    if "P" not in out.columns:
        out["P"] = 0.0

    out = out.rename(columns={"C": "call_gex", "P": "put_gex"})
    out["net_gex"] = out["call_gex"] + out["put_gex"]
    out = out.sort_values("strike").reset_index(drop=True)
    return out


def total_gex(gex_df: pd.DataFrame) -> float:
    return float(gex_df["gex"].sum())


# =========================
# 5) Call Wall / Put Wall
# =========================

def find_call_wall(strike_gex: pd.DataFrame) -> Tuple[float, float]:
    """
    Call Wall: call-side gamma concentration 最大的 strike
    """
    tmp = strike_gex.copy()
    idx = tmp["call_gex"].idxmax()
    return float(tmp.loc[idx, "strike"]), float(tmp.loc[idx, "call_gex"])


def find_put_wall(strike_gex: pd.DataFrame) -> Tuple[float, float]:
    """
    Put Wall: put-side gamma concentration（绝对值）最大的 strike
    """
    tmp = strike_gex.copy()
    idx = tmp["put_gex"].abs().idxmax()
    return float(tmp.loc[idx, "strike"]), float(tmp.loc[idx, "put_gex"])


# =========================
# 6) Gamma Flip / Zero Gamma
# =========================

def compute_total_gex_for_spot(
    inventory_df: pd.DataFrame,
    spot: float,
    valuation_ts: pd.Timestamp,
    config: ModelConfig = ModelConfig()
) -> float:
    gex_df = compute_gex_at_spot(
        inventory_df=inventory_df,
        spot=spot,
        valuation_ts=valuation_ts,
        config=config
    )
    return total_gex(gex_df)


def find_gamma_flip(
    inventory_df: pd.DataFrame,
    valuation_ts: pd.Timestamp,
    spot_min: float,
    spot_max: float,
    num_grid: int = 200,
    config: ModelConfig = ModelConfig()
) -> Dict[str, float]:
    """
    在 [spot_min, spot_max] 上网格搜索 + 线性插值找 Net GEX=0 的位置。
    更稳妥时可再加二分法。
    """
    if spot_min <= 0 or spot_max <= 0 or spot_max <= spot_min:
        raise ValueError("spot_min / spot_max 不合法")

    grid = np.linspace(spot_min, spot_max, num_grid)
    vals = np.array([
        compute_total_gex_for_spot(inventory_df, s, valuation_ts, config=config)
        for s in grid
    ])

    sign = np.sign(vals)
    cross_idx = np.where(sign[:-1] * sign[1:] <= 0)[0]

    result = {
        "flip_spot": np.nan,
        "left_spot": np.nan,
        "right_spot": np.nan,
        "left_gex": np.nan,
        "right_gex": np.nan,
    }

    if len(cross_idx) == 0:
        return result

    i = int(cross_idx[0])
    s1, s2 = grid[i], grid[i + 1]
    v1, v2 = vals[i], vals[i + 1]

    # 线性插值
    if abs(v2 - v1) < 1e-12:
        flip = 0.5 * (s1 + s2)
    else:
        flip = s1 - v1 * (s2 - s1) / (v2 - v1)

    result.update({
        "flip_spot": float(flip),
        "left_spot": float(s1),
        "right_spot": float(s2),
        "left_gex": float(v1),
        "right_gex": float(v2),
    })
    return result


# =========================
# 7) 顶层一键流程
# =========================

def build_institutional_levels(
    options: pd.DataFrame,
    trades: pd.DataFrame,
    valuation_ts: pd.Timestamp,
    current_spot: float,
    open_interest: Optional[pd.DataFrame] = None,
    config: ModelConfig = ModelConfig(),
    flip_range_pct: float = 0.15
) -> Dict[str, object]:
    """
    外部示例：基于成交推断 dealer inventory 的 levels 构建流程。
    该流程依赖逐笔 side/opening_flag/customer_type 等标签，不代表仓库当前
    Longbridge 数据条件下的生产主口径。

    输出：
    - inventory 明细
    - gex_detail 当前 spot 下逐合约 GEX
    - strike_gex 当前 spot 下逐 strike GEX
    - call_wall
    - put_wall
    - gamma_flip
    - total_gex
    """
    options2 = prepare_option_frame(options)
    trades2 = prepare_trade_frame(trades)

    dealer_pos = infer_dealer_signed_position_from_trades(trades2)
    inventory = merge_inventory(
        options=options2,
        dealer_pos=dealer_pos,
        fallback_open_interest=open_interest,
        oi_sign_rule="classic"
    )

    gex_detail = compute_gex_at_spot(
        inventory_df=inventory,
        spot=current_spot,
        valuation_ts=valuation_ts,
        config=config
    )
    strike_gex = aggregate_gex_by_strike(gex_detail)

    call_wall_strike, call_wall_value = find_call_wall(strike_gex)
    put_wall_strike, put_wall_value = find_put_wall(strike_gex)

    gamma_flip = find_gamma_flip(
        inventory_df=inventory,
        valuation_ts=valuation_ts,
        spot_min=current_spot * (1.0 - flip_range_pct),
        spot_max=current_spot * (1.0 + flip_range_pct),
        num_grid=200,
        config=config
    )

    return {
        "inventory": inventory,
        "gex_detail": gex_detail,
        "strike_gex": strike_gex,
        "call_wall": {
            "strike": call_wall_strike,
            "gex": call_wall_value,
        },
        "put_wall": {
            "strike": put_wall_strike,
            "gex": put_wall_value,
        },
        "gamma_flip": gamma_flip,
        "total_gex": float(gex_detail["gex"].sum()),
    }


# =========================
# 8) 使用示例
# =========================

if __name__ == "__main__":
    options = pd.DataFrame({
        "option_id": ["C100", "C105", "P95", "P90"],
        "option_type": ["C", "C", "P", "P"],
        "strike": [100, 105, 95, 90],
        "expiry": ["2026-03-20", "2026-03-20", "2026-03-20", "2026-03-20"],
        "iv": [0.22, 0.24, 0.25, 0.28],
        "rate": [0.03, 0.03, 0.03, 0.03],
        "div": [0.00, 0.00, 0.00, 0.00],
    })

    trades = pd.DataFrame({
        "option_id": ["C100", "C105", "P95", "P90", "C100", "P95"],
        "timestamp": [
            "2026-03-12 09:31:00",
            "2026-03-12 09:32:00",
            "2026-03-12 09:33:00",
            "2026-03-12 09:34:00",
            "2026-03-12 10:01:00",
            "2026-03-12 10:05:00",
        ],
        "qty": [300, 120, 500, 250, 100, 80],
        "side": ["buy", "sell", "buy", "buy", "sell", "sell"],
        "opening_flag": [1, 1, 1, 1, -1, -1],  # 开仓=1, 平仓=-1
        "customer_type": ["customer"] * 6,
    })

    open_interest = pd.DataFrame({
        "option_id": ["C100", "C105", "P95", "P90"],
        "open_interest": [2000, 1500, 2500, 1800],
    })

    result = build_institutional_levels(
        options=options,
        trades=trades,
        valuation_ts=pd.Timestamp("2026-03-12 10:30:00"),
        current_spot=100.0,
        open_interest=open_interest,
        config=ModelConfig(contract_multiplier=100, gex_scale_per_1pct=True),
        flip_range_pct=0.20
    )

    print("\n=== Call Wall ===")
    print(result["call_wall"])

    print("\n=== Put Wall ===")
    print(result["put_wall"])

    print("\n=== Gamma Flip ===")
    print(result["gamma_flip"])

    print("\n=== Total GEX ===")
    print(result["total_gex"])

    print("\n=== Strike GEX ===")
    print(result["strike_gex"])
