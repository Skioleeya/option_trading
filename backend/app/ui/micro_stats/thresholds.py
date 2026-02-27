"""MicroStats submodule — Business Thresholds.

做市商视角 (Market Maker Perspective)：
每个阈值都对应着做市商被迫调整对冲仓位的边界。

修改此文件可改变触发灵敏度，无需触碰 Presenter 或前端逻辑。
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. NET GEX  (Gamma Exposure 净头寸)
# ─────────────────────────────────────────────────────────────────────────────
# 做市商角度：GEX 代表全市场做市商的 Delta 对冲方向需求。
# - 正 GEX 越大 → 做市商越需要卖涨买跌 → 价格被"钉住"
# - 负 GEX      → 做市商需要追涨杀跌 → 价格加速
#
# 单位: Million USD (百万美元)
GEX_SUPER_PIN_THRESHOLD_M   = 1000  # >= 1000M → 市场像被磁铁锁住，极低波动
GEX_DAMPING_THRESHOLD_M     = 200   # >= 200M  → 温和阻尼，做市商小幅吸收波动
GEX_DEEP_NEGATIVE_THRESHOLD = -500  # <= -500M → 深度负 Gamma，极度加速

# ─────────────────────────────────────────────────────────────────────────────
# 2. WALL DYN  (Gamma Wall Dynamics — 墙体动态)
# ─────────────────────────────────────────────────────────────────────────────
# 做市商角度：做市商在大 OI 的 strike 处集中对冲 → 形成"墙"
# - 墙体上移 (RETREAT) → 阻力撤退，价格空间打开
# - 墙体加固 (SIEGE)   → 做市商在该价位集中反向对冲，价格难以突破
# - 量的增加 (REINFORCE) → 新的资金流入该 strike，是更强的信号
#
# Call Wall 状态集合 → 触发 SIEGE (围攻/大墙压顶)
WALL_SIEGE_STATES     = {"REINFORCED_WALL", "REINFORCED_SUPPORT"}

# Call Wall 撤退 → 上方空间打开
WALL_RETREAT_STATES   = {"RETREATING_RESISTANCE"}

# Put Wall 沦陷 → 下方支撑丢失
WALL_COLLAPSE_STATES  = {"RETREATING_SUPPORT"}

# 双墙对峙 → 两侧均被加固，做市商"人墙包围"
WALL_PINCH_CALL_STATES = {"REINFORCED_WALL"}
WALL_PINCH_PUT_STATES  = {"REINFORCED_SUPPORT"}

# ─────────────────────────────────────────────────────────────────────────────
# 3. MOMENTUM  (Agent A — VWAP 微信号)
# ─────────────────────────────────────────────────────────────────────────────
# 做市商角度：聪明资金的方向性流动会先在 VWAP 斜率上体现
# - 价格持续在 VWAP + 1σ 上方 + 正斜率 → 主动买盘主导
# - 价格持续在 VWAP - 1σ 下方 + 负斜率 → 主动卖盘主导
# - 中性区间 → 做市商双向对冲，方向不明

MOMENTUM_BULLISH_STATES = {"BULLISH"}   # 价格 > VWAP+1σ, 斜率为正
MOMENTUM_BEARISH_STATES = {"BEARISH"}   # 价格 < VWAP-1σ, 斜率为负
MOMENTUM_NEUTRAL_STATES = {"NEUTRAL", "IDLE", ""}

# ─────────────────────────────────────────────────────────────────────────────
# 4. VANNA  (Spot-Vol 相关性 — 期权隐含力场)
# ─────────────────────────────────────────────────────────────────────────────
# 做市商角度：Vanna = dDelta/dVol。做市商在 IV 变化时，其 Delta 对冲头寸会
# 被迫重新平衡，产生"Vanna 驱动"的方向性流动。
#
# DANGER_ZONE: Spot ↑ + IV ↑ → 做市商 Delta 增加 → 被迫追买 → 自我强化上涨
# GRIND_STABLE: Spot ↑ + IV ↓ → 做市商 Delta 减少 → 被迫卖出 → 压制/慢涨
# VANNA_FLIP:  相关性在极短时间内从大负变小 → 对冲方向突然逆转 → 最危险的状态
# NORMAL:       相关性处于中性区间

VANNA_DANGER_STATES  = {"DANGER_ZONE", "DANGER"}   # 正相关 → 追涨动能
VANNA_CMPRS_STATES   = {"GRIND_STABLE", "CMPRS"}   # 负相关 → 压力积累
VANNA_FLIP_STATES    = {"VANNA_FLIP", "FLIP"}       # 相关性翻转 → 极端事件
VANNA_NORMAL_STATES  = {"NORMAL", "NEUTRAL"}
VANNA_WARMING_STATES = {"UNAVAILABLE"}              # 数据积累中
