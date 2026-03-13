"""[P0] Agent G (Decision / Fusion) configuration — highest change frequency."""

from pydantic import Field

from shared.config._base import BaseConfig


class AgentGConfig(BaseConfig):
    """Decision-fusion agent: GEX, VRP, MTF, weights, jump detection."""

    # Wall proximity
    agent_g_wall_magnet_pct: float = Field(
        default=0.3, description="Distance % to consider 'Approaching' a Wall"
    )
    agent_g_wall_breakout_pct: float = Field(
        default=0.1, description="Distance % beyond Wall to consider 'Breach'"
    )

    # ── IV Regimes ─────────────────────────────────────────────────────────────
    iv_low_max: float = Field(
        default=12.0, description="IV < this = LOW regime (crushed vol, Long Gamma)"
    )
    iv_normal_max: float = Field(
        default=20.0, description="IV < this = NORMAL regime (typical, Neutral strategies)"
    )
    iv_elevated_max: float = Field(
        default=30.0, description="IV < this = ELEVATED regime (fear, Short Vol)"
    )
    iv_high_max: float = Field(
        default=35.0, description="IV < this = HIGH regime (volatility decay zone, 30-35%)"
    )

    # ── VRP (Variance Risk Premium) ────────────────────────────────────────────
    vrp_baseline_hv: float = Field(
        default=13.5,
        description=(
            "PP-1 FIX: VRP 计算所用的历史波动率基线 (annualized %). "
            "默认 13.5 = SPY 结构性 HV。可通过环境变量 VRP_BASELINE_HV 覆盖。"
        ),
    )
    vrp_cheap_threshold: float = Field(
        default=-1.5, description="VRP < this = Options CHEAP (Vol sellers underpricing risk)"
    )
    vrp_expensive_threshold: float = Field(
        default=3.5, description="VRP > this = Options EXPENSIVE (Requires strict hedging)"
    )
    vrp_trap_threshold: float = Field(
        default=7.0,
        description="VRP > this = THETA TRAP (Extreme premium, strict mean-reversion expected)",
    )
    vrp_veto_threshold: float = Field(
        default=8.0,
        description=(
            "Phase 25A — VRP Veto Gate (Paper: Muravyev et al. SSRN #4019647). "
            "When VRP > this value, all LONG_CALL/PUT signals are vetoed as NO_TRADE. "
            "Default 8.0 = 2× the TRAP threshold, i.e. extreme rare event only."
        ),
    )
    vrp_bargain_boost: float = Field(
        default=1.15,
        description=(
            "Phase 25A — Confidence multiplier applied when VRP is in BARGAIN territory. "
            "Default 1.15 = +15% confidence boost."
        ),
    )
    guard_vrp_entry_threshold: float = Field(
        default=15.0,
        description="GuardRail VRP veto entry threshold in percent points (legacy 0.15 => 15.0).",
    )
    guard_vrp_exit_threshold: float = Field(
        default=13.0,
        description="GuardRail VRP veto exit threshold in percent points (legacy 0.13 => 13.0).",
    )
    guard_vrp_min_hold_ticks: int = Field(
        default=3,
        description="Minimum ticks to hold VRP veto once activated.",
    )
    guard_vrp_exit_confirm_ticks: int = Field(
        default=2,
        description="Consecutive below-exit ticks required before releasing VRP veto.",
    )
    guard_drawdown_limit_usd: float = Field(
        default=-500.0,
        description="GuardRail drawdown stop threshold in USD.",
    )
    guard_drawdown_cooldown_minutes: float = Field(
        default=30.0,
        description="Cooldown minutes after drawdown guard is triggered.",
    )
    guard_session_window_minutes: int = Field(
        default=15,
        description="Session guard opening/closing window in minutes.",
    )
    guard_session_confidence_reduction: float = Field(
        default=0.30,
        description="Session guard confidence reduction ratio inside opening/closing windows.",
    )

    # ── Jump Detection (Phase 27) ──────────────────────────────────────────────
    jump_z_threshold: float = Field(
        default=3.0,
        description="Phase 27.1 — Z-Score threshold for price jump detection (|Z| > threshold).",
    )
    jump_lockout_seconds: int = Field(
        default=60,
        description="Phase 27.3 — Duration of signal halt after a jump is detected.",
    )

    # ── GEX Regime Thresholds ─────────────────────────────────────────────────
    gex_neutral_threshold: float = Field(
        default=20000.0, description="|GEX| < 20000M (20B) = NEUTRAL regime"
    )
    gex_damping_threshold: float = Field(
        default=20000.0, description="20000M <= |GEX| = DAMPING regime entry (positive GEX)"
    )
    gex_extreme_threshold: float = Field(
        default=50000.0, description="|GEX| upper bound for DAMPING regime (< 50000M / 50B)"
    )
    gex_super_pin_threshold: float = Field(
        default=100000.0, description="|GEX| >= 100000M (100B) = SUPER_PIN regime"
    )
    gex_strong_negative: float = Field(
        default=-50000.0, description="GEX <= -50000M (-50B) = strong NEGATIVE_ACCELERATION"
    )
    gex_strong_positive: float = Field(
        default=50000.0, description="GEX >= 50000M (50B) = strong POSITIVE_DAMPING"
    )
    gex_acceleration_threshold: float = Field(
        default=0, description="net_gex < 0 = ACCELERATION regime (any negative)"
    )
    gex_moderate_threshold: float = Field(
        default=30000.0, description="|GEX| >= 30000M (30B) = MODERATE intensity (legacy)"
    )
    gex_accel_threshold: float = Field(
        default=10000.0,
        description=(
            "PP-4 FIX: net_gex > 此值时激活加速置信度增益 (当前口径 10000M / 10B). "
            "可通过环境变量 GEX_ACCEL_THRESHOLD 覆盖。"
        ),
    )
    gex_accel_boost_bearish: float = Field(
        default=1.20,
        description="PP-4 FIX: 负 Gamma 环境下 BEARISH 信号的置信度增益倍数 (原硬编码 1.20)。",
    )
    gex_accel_boost_bullish: float = Field(
        default=1.15,
        description="PP-4 FIX: 负 Gamma 环境下 BULLISH 信号的置信度增益倍数 (原硬编码 1.15)。",
    )

    # ── AgentG Component Weights ───────────────────────────────────────────────
    agent_g_iv_weight: float = Field(default=0.25, description="IV Velocity base weight")
    agent_g_wall_weight: float = Field(default=0.30, description="Wall Dynamics base weight")
    agent_g_vanna_weight: float = Field(default=0.20, description="Vanna Flow base weight")
    agent_g_mtf_weight: float = Field(default=0.25, description="Multi-Timeframe Consensus base weight")
    agent_g_vib_weight: float = Field(
        default=0.20,
        description=(
            "PP-2/PP-6 FIX: Volume Imbalance 分量基础权重 (原硬编码 0.20)。"
            "可通过环境变量 AGENT_G_VIB_WEIGHT 覆盖。"
        ),
    )
    agent_g_micro_flow_weight: float = Field(
        default=0.12,
        description=(
            "Phase 3: L2 Micro Flow (toxicity + bbo_imbalance) 分量基础权重。"
            "比 MTF/VIB 低，避免单因子过拟合 (Paper 4: OFI alpha 衰减快)。"
        ),
    )
    micro_flow_toxicity_threshold: float = Field(
        default=0.25,
        description=(
            "Phase 3: micro_flow 方向信号触发门限。"
            "|micro_score| < 0.25 时视为噪音不产生方向信号。"
        ),
    )

    # ── MTF Alignment Hysteresis (PP-2 Fix) ───────────────────────────────────
    mtf_alignment_damp_entry: float = Field(
        default=0.34,
        description="PP-2 FIX: MTF alignment 低于此值时激活置信度阻尼 (原硬编码 0.34)。",
    )
    mtf_alignment_damp_exit: float = Field(
        default=0.38,
        description="PP-2 FIX: MTF alignment 高于此值时退出置信度阻尼 (原硬编码 0.38)。",
    )
    mtf_alignment_ewma_alpha: float = Field(
        default=0.30,
        description=(
            "PP-2 FIX: MTF alignment EWMA 平滑因子。"
            "0.0 = 纯历史（无响应），1.0 = 瞬时值（无平滑）。"
            "默认 0.30 消除单 tick 离散跳跃。"
        ),
    )

    # ── MTF Consensus Weights ─────────────────────────────────────────────────
    mtf_weight_1min: float = Field(
        default=0.35, description="1min timeframe weight for MTF consensus (entry trigger)"
    )
    mtf_weight_5min: float = Field(
        default=0.35, description="5min timeframe weight for MTF consensus (core rhythm)"
    )
    mtf_weight_15min: float = Field(
        default=0.30, description="15min timeframe weight for MTF consensus (trend background)"
    )

    # MTF Window Seconds
    mtf_window_seconds_1min: int = Field(
        default=120, description="IV tracker window for 1min timeframe (120s for Exhaustion sync)"
    )
    mtf_window_seconds_5min: int = Field(
        default=300, description="IV tracker window for 5min timeframe"
    )
    mtf_window_seconds_15min: int = Field(
        default=900, description="IV tracker window for 15min timeframe"
    )

    # IV / Spot velocity
    iv_roc_threshold_pct: float = Field(
        default=2.0, description="IV change threshold (pp) to classify as significant"
    )
    spot_roc_threshold_pct: float = Field(
        default=0.03, description="Spot move threshold (%) for divergence detection"
    )

    # Vanna Flow
    vanna_danger_zone_threshold: float = Field(
        default=0.45,
        description="Spot-Vol correlation > 0.45 (Positive correlation warns of directional break/bubble)",
    )
    vanna_grind_stable_threshold: float = Field(
        default=-0.75,
        description="Inverse correlation < -0.75 (Healthy stable market regime)",
    )

    # Wall Migration
    wall_snapshot_interval_seconds: float = Field(
        default=900, description="Wall snapshot interval (900 = 15 minutes)"
    )
    wall_displacement_threshold: float = Field(
        default=1.0, description="Strike points to consider wall 'moved'"
    )
    volume_reinforcement_threshold: int = Field(
        default=500, description="Contracts for 'significant volume' reinforcement"
    )

    # Fusion threshold
    fusion_confidence_threshold: float = Field(
        default=0.75,
        description=(
            "Minimum fused-signal confidence for Fusion Engine to override Trend logic "
            "(AgentG.decide). Values in [0, 1]."
        ),
    )

    # Put-Call Parity
    risk_free_rate: float = Field(
        default=0.05,
        description="Annual risk-free rate used for Put-Call Parity implied spot calculation",
    )
    implied_spot_pcp_strikes: int = Field(
        default=10,
        description="Number of ATM-region strikes used in PCP implied-spot calculation",
    )
