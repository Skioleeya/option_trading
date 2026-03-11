"""MicroStats submodule — Private Palette.

亚洲龙风格暗色调色板 (Asian Dragon Dark Mode)：
规则：红涨绿跌。阻力 = 红系，支撑 = 绿系，极端 = 紫系，警告 = 琥珀系。

此文件仅供 MicroStats 内部使用。跨模块共享色彩放在 theme.py。
"""

# ────────────────── 图标色 (Icon Colors) ──────────────────────────────────────
# 对应截图中右上角的小图标
NET_GEX_ICON_COLOR  = "text-[#a855f7]"   # 紫色脉冲 — Gamma 场是"隐形力场"
WALL_DYN_ICON_COLOR = "text-[#f59e0b]"   # 琥珀船锚 — 墙体是"锚点"
VANNA_ICON_COLOR    = "text-[#22d3ee]"   # 青蓝闪电 — Vanna 流是"电流"
MOMENTUM_ICON_COLOR = "text-[#71717a]"   # 灰色横线 — Momentum 默认中性

# ────────────────── NET GEX 专用 Badge ────────────────────────────────────────
# SUPER_PIN: 极度锁定 → 亮琥珀实心（警告色，市场失去弹性）
BADGE_GEX_SUPER_PIN    = "badge-amber"

# DAMPING: GEX 阻尼 → 绿色空心（做市商在稳定秩序）
BADGE_GEX_DAMPING      = "badge-hollow-green"

# ACCELERATION: 负 GEX 加速 → 紫色空心（市场进入危险加速区）
BADGE_GEX_ACCELERATION = "badge-hollow-purple"

# NEUTRAL: 无方向 → 中性灰
BADGE_GEX_NEUTRAL      = "badge-neutral"

# ────────────────── WALL DYN 专用 Badge ───────────────────────────────────────
# SIEGE: 墙体加固 → 琥珀空心（警示：价格在大墙下方，需要更多能量才能突破）
BADGE_WALL_SIEGE       = "badge-hollow-amber"

# RETREAT ↑: 阻力墙撤退（上涨语义）→ 红色实心
BADGE_WALL_RETREAT_UP   = "badge-red"

# RETREAT ↓: 支撑墙后撤（下跌语义）→ 绿色实心
BADGE_WALL_RETREAT_DOWN = "badge-green"

# 兼容旧键
BADGE_WALL_RETREAT      = BADGE_WALL_RETREAT_UP

# COLLAPSE: 支撑墙沦陷 → 绿色实心（下方支撑丢失，做市商 Put Delta 减少）
BADGE_WALL_COLLAPSE    = "badge-green"

# PINCH: 双墙对峙/钳形 → 紫色实心（被双侧大 OI 夹住，随时可能爆发）
BADGE_WALL_PINCH       = "badge-purple"

# STABLE: 无明显动态 → 中性灰
BADGE_WALL_STABLE      = "badge-neutral"

# BREACH: 墙体被击穿（方向未定但风险极高）→ 琥珀实心风险提示
BADGE_WALL_BREACH      = "badge-amber"

# DECAY: 尾盘衰减 → 中性灰
BADGE_WALL_DECAY       = "badge-neutral"

# UNAVAILABLE: 冷启动/缺数 → 中性灰
BADGE_WALL_UNAVAILABLE = "badge-neutral"

# ────────────────── MOMENTUM 专用 Badge ───────────────────────────────────────
# BULLISH: 上方 VWAP+σ → 红色实心（亚洲龙：红色=涨）
BADGE_MOM_BULLISH      = "badge-red"

# BEARISH: 下方 VWAP-σ → 绿色实心（亚洲龙：绿色=跌）
BADGE_MOM_BEARISH      = "badge-green"

# SIDE/NEUTRAL: 没有确定方向 → 中性灰
BADGE_MOM_SIDE         = "badge-neutral"

# ────────────────── VANNA 专用 Badge ──────────────────────────────────────────
# DANGER_ZONE: Spot↑ + IV↑ → 红色实心（做市商追买 → 追涨动能，高危信号）
BADGE_VANNA_DANGER     = "badge-red"

# GRIND_STABLE / CMPRS: Spot↑ + IV↓ → 青蓝空心（IV 压缩 → 压制慢涨）
BADGE_VANNA_CMPRS      = "badge-hollow-cyan"

# VANNA_FLIP: 相关性突然逆转 → 紫色实心（最极端：做市商对冲方向突变）
BADGE_VANNA_FLIP       = "badge-purple"

# NORMAL / NEUTRAL → 中性灰
BADGE_VANNA_NORMAL     = "badge-neutral"

# UNAVAILABLE: 数据不足 → 更暗的中性（表示"正在预热"）
BADGE_VANNA_WARMING    = "badge-neutral"
