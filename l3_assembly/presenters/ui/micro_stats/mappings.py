"""MicroStats submodule — UI State Mappings.

将后端业务状态字符串 → 前端 (label, badge) 对。
所有颜色统一从本模块的 palette.py 取，不直接写颜色代码。

数据流: Agent 状态字符串 → mappings 字典查找 → Presenter 打包 → 前端渲染
"""

from l3_assembly.presenters.ui.micro_stats import palette


# ─────────────────────────────────────────────────────────────────────────────
# NET GEX — Gamma Exposure 净头寸状态
# 做市商视角：每个状态代表市场 Gamma 场的当前物理特性
# ─────────────────────────────────────────────────────────────────────────────
GEX_REGIME_MAP: dict[str, dict] = {
    # 极度锁定：GEX >= 1000M，市场被"磁铁"固定，做市商全线压制波动
    "SUPER_PIN":    {"label": "SUPER PIN",  "badge": palette.BADGE_GEX_SUPER_PIN},

    # Gamma 阻尼：200M~1000M，做市商温和对冲，价格弹性受限
    "DAMPING":      {"label": "DAMPING",    "badge": palette.BADGE_GEX_DAMPING},

    # 负 Gamma 加速：GEX < 0，做市商追涨杀跌，提供加速而非抑制
    "ACCELERATION": {"label": "VOLATILE",   "badge": palette.BADGE_GEX_ACCELERATION},

    # 中性区间：GEX 绝对值 < 200M，Gamma 力场影响弱
    "NEUTRAL":      {"label": "NEUTRAL",    "badge": palette.BADGE_GEX_NEUTRAL},
}


# ─────────────────────────────────────────────────────────────────────────────
# WALL DYN — Gamma Wall Dynamics 墙体动态
# 做市商视角：大 OI 的 strike 处会形成对冲集中带（墙体），其动态揭示主力意图
# ─────────────────────────────────────────────────────────────────────────────
WALL_DYNAMICS_MAP: dict[str, dict] = {
    # 墙体被击穿（可能是向上 squeeze 或向下 cascade）→ 优先提示风险
    "BREACH":             {"label": "BREACH",   "badge": palette.BADGE_WALL_BREACH},

    # 14:00 ET 后衰减期，墙体参考价值下降
    "DECAY":              {"label": "DECAY",    "badge": palette.BADGE_WALL_DECAY},

    # 正上方/正下方大 OI 加固 → 被大墙压制，需要强烈买盘或卖盘才能突破
    "SIEGE":              {"label": "SIEGE",    "badge": palette.BADGE_WALL_SIEGE},

    # 上方阻力墙撤退 → Call Wall 上移，上方空间打开，做市商 Call Delta 减少
    "RETREAT":            {"label": "RETREAT",  "badge": palette.BADGE_WALL_RETREAT},

    # 下方支撑墙沦陷 → Put Wall 下移，支撑丢失，做市商 Put Delta 减少  
    "COLLAPSE":           {"label": "COLLAPSE", "badge": palette.BADGE_WALL_COLLAPSE},

    # 上下双墙对峙 → 双壁夹攻，极度压缩，随时可能单向爆发
    "PINCH":              {"label": "PINCH",    "badge": palette.BADGE_WALL_PINCH},

    # 无明显移动 → 做市商保持当前对冲仓位不变
    "STABLE":             {"label": "STABLE",   "badge": palette.BADGE_WALL_STABLE},

    # 冷启动 / 缺数
    "UNAVAILABLE":        {"label": "WARM↑",    "badge": palette.BADGE_WALL_UNAVAILABLE},

    # 兼容旧版字段名
    "REINFORCED_WALL":       {"label": "SIEGE",    "badge": palette.BADGE_WALL_SIEGE},
    "REINFORCED_SUPPORT":    {"label": "SIEGE",    "badge": palette.BADGE_WALL_SIEGE},
    "RETREATING_RESISTANCE": {"label": "RETREAT",  "badge": palette.BADGE_WALL_RETREAT},
    "RETREATING_SUPPORT":    {"label": "COLLAPSE", "badge": palette.BADGE_WALL_COLLAPSE},
    "BREACHED":              {"label": "BREACH",   "badge": palette.BADGE_WALL_BREACH},
    "DECAYING":              {"label": "DECAY",    "badge": palette.BADGE_WALL_DECAY},
    "UNAVAILABLE":           {"label": "WARM↑",    "badge": palette.BADGE_WALL_UNAVAILABLE},
}


# ─────────────────────────────────────────────────────────────────────────────
# MOMENTUM — Agent A VWAP 微信号
# 亚洲龙风格：红色 = 上涨动能（多），绿色 = 下跌动能（空）
# ─────────────────────────────────────────────────────────────────────────────
MOMENTUM_MAP: dict[str, dict] = {
    # 价格在 VWAP+1σ 上方 + 正斜率 → 主动买盘主导，看涨
    "BULLISH": {"label": "LONG",    "badge": palette.BADGE_MOM_BULLISH},

    # 价格在 VWAP-1σ 下方 + 负斜率 → 主动卖盘主导，看跌
    "BEARISH": {"label": "SHORT",   "badge": palette.BADGE_MOM_BEARISH},

    # 在 VWAP 附近震荡，方向不明 → 做市商观望
    "NEUTRAL": {"label": "SIDE",    "badge": palette.BADGE_MOM_SIDE},

    # 系统初始化中
    "IDLE":    {"label": "SIDE",    "badge": palette.BADGE_MOM_SIDE},
    "":        {"label": "SIDE",    "badge": palette.BADGE_MOM_SIDE},
}


# ─────────────────────────────────────────────────────────────────────────────
# VANNA — Spot-Vol 相关性 (Vanna Flow 期权隐含力场)
# 做市商视角：Vanna = dDelta/dVol，IV 的涨跌驱动做市商强制重平衡 Delta
# ─────────────────────────────────────────────────────────────────────────────
VANNA_STATE_MAP: dict[str, dict] = {
    # Spot ↑ + IV ↑ → 做市商 Delta 增加 → 被迫追买 → 自我强化上涨（极危险）
    "DANGER_ZONE":  {"label": "DANGER",  "badge": palette.BADGE_VANNA_DANGER},
    "DANGER":       {"label": "DANGER",  "badge": palette.BADGE_VANNA_DANGER},

    # Spot ↑ + IV ↓ → 做市商 Delta 减少 → 被迫卖出 → 慢涨中隐藏的压力积累
    "GRIND_STABLE": {"label": "CMPRS",   "badge": palette.BADGE_VANNA_CMPRS},
    "CMPRS":        {"label": "CMPRS",   "badge": palette.BADGE_VANNA_CMPRS},

    # 相关性在 2 分钟内从大负突变接近零 → 对冲方向急剧逆转（最极端信号）
    "VANNA_FLIP":   {"label": "FLIP ⚡",  "badge": palette.BADGE_VANNA_FLIP},
    "FLIP":         {"label": "FLIP ⚡",  "badge": palette.BADGE_VANNA_FLIP},

    # 中性：Spot 与 IV 相关性处于 [-0.3, +0.3] 区间
    "NORMAL":       {"label": "NORMAL",  "badge": palette.BADGE_VANNA_NORMAL},
    "NEUTRAL":      {"label": "NEUTRAL", "badge": palette.BADGE_VANNA_NORMAL},

    # 数据积累不足，窗口未满 → 前端显示"预热"
    "UNAVAILABLE":  {"label": "WARM↑",   "badge": palette.BADGE_VANNA_WARMING},
}
