"""
专业级 BTM 光储财务测算系统 v3.0
Professional BTM PV+BESS Financial Modelling System
South Africa C&I Megaflex / Miniflex Tariff 2025/26 | 8760-Hour Physical Dispatch Engine
Section 12B Accelerated Depreciation | Huawei SA Digital Power
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
import warnings
from datetime import date as _date
warnings.filterwarnings("ignore")

# SA 2025 公众假期 / SA 2025 Public Holidays (off-peak all day like weekends)
SA_PUBLIC_HOLIDAYS_2025 = {
    _date(2025, 1, 1),   # New Year's Day
    _date(2025, 3, 21),  # Human Rights Day
    _date(2025, 4, 18),  # Good Friday
    _date(2025, 4, 21),  # Family Day
    _date(2025, 4, 27),  # Freedom Day
    _date(2025, 5, 1),   # Workers' Day
    _date(2025, 6, 16),  # Youth Day
    _date(2025, 8, 9),   # National Women's Day
    _date(2025, 9, 24),  # Heritage Day
    _date(2025, 12, 16), # Day of Reconciliation
    _date(2025, 12, 25), # Christmas Day
    _date(2025, 12, 26), # Day of Goodwill
}

try:
    import folium
    from streamlit_folium import st_folium
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# 页面配置 / Page Configuration
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BTM PV+BESS Financial Modelling System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# 全局样式 / Global Styles
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

    :root {
        --primary: #00E5A0;
        --secondary: #FF6B35;
        --accent: #4ECDC4;
        --bg-dark: #0A0E1A;
        --bg-card: #111827;
        --bg-input: #1C2333;
        --text-main: #E8ECF0;
        --text-dim: #8B95A3;
        --border: #2D3748;
        --warning: #F6C90E;
        --danger: #FF4444;
    }

    html, body, .stApp {
        background-color: var(--bg-dark) !important;
        color: var(--text-main) !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }

    .main-header {
        background: linear-gradient(135deg, #0A0E1A 0%, #111827 50%, #0A1628 100%);
        border-bottom: 1px solid var(--primary);
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .main-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.4rem;
        font-weight: 600;
        color: var(--primary);
        letter-spacing: 0.05em;
        margin: 0;
    }

    .sub-title {
        font-size: 0.72rem;
        color: var(--text-dim);
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: 0.08em;
    }

    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-left: 3px solid var(--primary);
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.6rem;
    }

    .metric-label {
        font-size: 0.68rem;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-family: 'IBM Plex Mono', monospace;
    }

    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--primary);
        font-family: 'IBM Plex Mono', monospace;
        line-height: 1.2;
    }

    .metric-unit {
        font-size: 0.68rem;
        color: var(--text-dim);
        font-family: 'IBM Plex Mono', monospace;
    }

    .section-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: var(--primary);
        text-transform: uppercase;
        letter-spacing: 0.12em;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.4rem;
        margin: 1rem 0 0.6rem 0;
    }

    .warning-box {
        background: rgba(246, 201, 14, 0.1);
        border: 1px solid var(--warning);
        border-radius: 6px;
        padding: 0.6rem 0.8rem;
        font-size: 0.78rem;
        color: var(--warning);
        font-family: 'IBM Plex Mono', monospace;
    }

    .success-box {
        background: rgba(0, 229, 160, 0.08);
        border: 1px solid var(--primary);
        border-radius: 6px;
        padding: 0.6rem 0.8rem;
        font-size: 0.78rem;
        color: var(--primary);
        font-family: 'IBM Plex Mono', monospace;
    }

    .info-box {
        background: rgba(78, 205, 196, 0.08);
        border: 1px solid var(--accent);
        border-radius: 6px;
        padding: 0.6rem 0.8rem;
        font-size: 0.78rem;
        color: var(--accent);
        font-family: 'IBM Plex Mono', monospace;
    }

    .param-label {
        font-size: 0.72rem;
        color: var(--text-dim);
        font-family: 'IBM Plex Mono', monospace;
        margin-bottom: 0.1rem;
    }

    .derived-value {
        background: rgba(0,229,160,0.06);
        border: 1px solid rgba(0,229,160,0.3);
        border-radius: 4px;
        padding: 0.3rem 0.6rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
        color: var(--primary);
        text-align: center;
        margin-bottom: 0.4rem;
    }

    .tariff-winter {
        border-left: 3px solid #4ECDC4;
        padding-left: 0.5rem;
        margin-bottom: 0.3rem;
    }

    .tariff-summer {
        border-left: 3px solid #F6C90E;
        padding-left: 0.5rem;
        margin-bottom: 0.3rem;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: var(--text-dim);
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--primary) !important;
    }

    .stButton > button {
        background: transparent;
        border: 1px solid var(--primary);
        color: var(--primary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        letter-spacing: 0.06em;
        border-radius: 4px;
        transition: all 0.2s ease;
        padding: 0.3rem 0.8rem;
    }

    .stButton > button:hover {
        background: var(--primary);
        color: var(--bg-dark);
    }

    .stDownloadButton > button {
        background: transparent;
        border: 1px solid var(--accent);
        color: var(--accent);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        border-radius: 4px;
    }

    /* Compact expander styling */
    .streamlit-expanderHeader {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.78rem !important;
        color: var(--text-main) !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 4px !important;
        padding: 0.4rem 0.8rem !important;
    }

    .streamlit-expanderContent {
        background: rgba(17, 24, 39, 0.5) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        padding: 0.6rem !important;
    }

    div[data-testid="stNumberInput"] input {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
        background: var(--bg-input) !important;
        color: var(--text-main) !important;
    }

    .eol-badge {
        display: inline-block;
        background: rgba(255, 107, 53, 0.15);
        border: 1px solid var(--secondary);
        color: var(--secondary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        padding: 0.15rem 0.5rem;
        border-radius: 20px;
    }

    /* Hide default sidebar toggle */
    [data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 常量定义 / Constants
# ─────────────────────────────────────────────────────────────

# 南非 Eskom Megaflex 正确季节定义 /
# SA Megaflex: High season = June, July, August ONLY (May is low season!)
WINTER_MONTHS = {6, 7, 8}

# ─────────────────────────────────────────────────────────────
# Eskom 2025/26 Tariff Database
# Tuple: (w_peak, w_standard, w_off_peak, s_peak, s_standard, s_off_peak) ZAR/kWh incl VAT
# = active energy charge + legacy charge (both incl VAT, from Tariff Booklet 2025/26)
# TOU applies to Megaflex & Miniflex. Nightsave = flat rate (all periods same price).
# ─────────────────────────────────────────────────────────────
TARIFF_DB = {
    # ── Megaflex Non-local Authority (p13) ────────────────────────────────────
    "Megaflex ≤300km <500V":        (8.1348, 2.2302, 1.5740, 3.5294, 2.0990, 1.5740),
    "Megaflex ≤300km 500V-66kV":    (7.9249, 2.1727, 1.5335, 3.4383, 2.0449, 1.5335),
    "Megaflex ≤300km 66-132kV":     (7.3544, 2.0162, 1.4231, 3.1908, 1.8977, 1.4231),
    "Megaflex ≤300km >132kV":       (6.8579, 1.8801, 1.3271, 2.9754, 1.7696, 1.3271),
    "Megaflex 300-600km <500V":     (8.2134, 2.2499, 1.5871, 3.5620, 2.1174, 1.5871),
    "Megaflex 300-600km 500V-66kV": (8.0017, 2.1919, 1.5464, 3.4701, 2.0628, 1.5464),
    "Megaflex 300-600km 66-132kV":  (7.4256, 2.0341, 1.4350, 3.2203, 1.9143, 1.4350),
    "Megaflex 300-600km >132kV":    (6.9243, 1.8968, 1.3381, 3.0029, 1.7850, 1.3381),
    "Megaflex 600-900km <500V":     (8.2922, 2.2696, 1.6003, 3.5947, 2.1357, 1.6003),
    "Megaflex 600-900km 500V-66kV": (8.0784, 2.2111, 1.5591, 3.5020, 2.0807, 1.5591),
    "Megaflex 600-900km 66-132kV":  (7.4967, 2.0518, 1.4468, 3.2499, 1.9310, 1.4468),
    "Megaflex 600-900km >132kV":    (6.9906, 1.9134, 1.3492, 3.0305, 1.8005, 1.3492),
    "Megaflex >900km <500V":        (8.3710, 2.2892, 1.6135, 3.6274, 2.1541, 1.6135),
    "Megaflex >900km 500V-66kV":    (8.1551, 2.2303, 1.5719, 3.5338, 2.0985, 1.5719),
    "Megaflex >900km 66-132kV":     (7.5679, 2.0697, 1.4588, 3.2793, 1.9475, 1.4588),
    "Megaflex >900km >132kV":       (7.0570, 1.9299, 1.3601, 3.0580, 1.8160, 1.3601),
    # ── Miniflex Non-local Authority (p20) — same energy rates as Megaflex ───
    "Miniflex ≤300km <500V":        (8.1348, 2.2302, 1.5740, 3.5294, 2.0990, 1.5740),
    "Miniflex ≤300km 500V-66kV":    (7.9249, 2.1727, 1.5335, 3.4383, 2.0449, 1.5335),
    "Miniflex ≤300km 66-132kV":     (7.3544, 2.0162, 1.4231, 3.1908, 1.8977, 1.4231),
    "Miniflex ≤300km >132kV":       (6.8579, 1.8801, 1.3271, 2.9754, 1.7696, 1.3271),
    "Miniflex 300-600km <500V":     (8.2134, 2.2499, 1.5871, 3.5620, 2.1174, 1.5871),
    "Miniflex 300-600km 500V-66kV": (8.0017, 2.1919, 1.5464, 3.4701, 2.0628, 1.5464),
    "Miniflex 300-600km 66-132kV":  (7.4256, 2.0341, 1.4350, 3.2203, 1.9143, 1.4350),
    "Miniflex 300-600km >132kV":    (6.9243, 1.8968, 1.3381, 3.0029, 1.7850, 1.3381),
    "Miniflex 600-900km <500V":     (8.2922, 2.2696, 1.6003, 3.5947, 2.1357, 1.6003),
    "Miniflex 600-900km 500V-66kV": (8.0784, 2.2111, 1.5591, 3.5020, 2.0807, 1.5591),
    "Miniflex 600-900km 66-132kV":  (7.4967, 2.0518, 1.4468, 3.2499, 1.9310, 1.4468),
    "Miniflex 600-900km >132kV":    (6.9906, 1.9134, 1.3492, 3.0305, 1.8005, 1.3492),
    "Miniflex >900km <500V":        (8.3710, 2.2892, 1.6135, 3.6274, 2.1541, 1.6135),
    "Miniflex >900km 500V-66kV":    (8.1551, 2.2303, 1.5719, 3.5338, 2.0985, 1.5719),
    "Miniflex >900km 66-132kV":     (7.5679, 2.0697, 1.4588, 3.2793, 1.9475, 1.4588),
    "Miniflex >900km >132kV":       (7.0570, 1.9299, 1.3601, 3.0580, 1.8160, 1.3601),
    # ── Nightsave Urban Non-local Authority (p22) — flat energy, no TOU arbitrage
    # All 6 period prices identical per season; BESS peak-shaving via demand charge not modelled
    "Nightsave ≤300km <500V":       (2.1991, 2.1991, 2.1991, 2.1227, 2.1227, 2.1227),
    "Nightsave ≤300km 500V-66kV":   (2.1423, 2.1423, 2.1423, 2.0679, 2.0679, 2.0679),
    "Nightsave ≤300km 66-132kV":    (1.9881, 1.9881, 1.9881, 1.9191, 1.9191, 1.9191),
    "Nightsave ≤300km >132kV":      (1.8540, 1.8540, 1.8540, 1.7895, 1.7895, 1.7895),
    # ── PPA (Power Purchase Agreement) — flat rate, user-defined ─────────────
    # 所有时段同价；用户在 UI 中输入单一 PPA 单价
    # All periods same price; user sets a single PPA rate in the UI
    "PPA 自定义 (flat rate)":          None,   # sentinel: UI shows PPA rate input
    # ── Custom — manual input, no auto-populate ──────────────────────────────
    "Custom (manual)":               None,
}

# ─────────────────────────────────────────────────────────────
# Huawei LUNA2000-2236-1S 官方 SOH 衰减表 (1C, DOD100%, ≤40°C)
# 来源: Utility Smart String Grid Forming ESS 2.0 Performance Guide p10
# key = 年等效循环次数 / annual equivalent full cycles
# value = [SOH year0, year1, ..., yearN]  (1.0 = 100%)
# EoL threshold = 60% (华为官方声明 / Huawei official)
# ─────────────────────────────────────────────────────────────
BESS_EOL_SOH = 0.60   # 低于此值视为退役 / EoL threshold

HUAWEI_SOH_TABLE: dict[int, list[float]] = {
    292: [1.0000,0.9552,0.9323,0.9113,0.8914,0.8724,0.8538,0.8355,0.8175,
          0.7999,0.7826,0.7657,0.7490,0.7326,0.7166,0.7008,0.6853,0.6701,
          0.6552,0.6405,0.6262],
    365: [1.0000,0.9509,0.9243,0.8996,0.8762,0.8536,0.8315,0.8098,0.7887,
          0.7681,0.7479,0.7281,0.7089,0.6900,0.6716,0.6536,0.6361,0.6189,
          0.6021],
    475: [1.0000,0.9446,0.9122,0.8822,0.8535,0.8255,0.7985,0.7723,0.7468,
          0.7221,0.6980,0.6748,0.6521,0.6302,0.6089],
    548: [1.0000,0.9403,0.9043,0.8706,0.8384,0.8072,0.7771,0.7479,0.7198,
          0.6927,0.6665,0.6411,0.6166],
    657: [1.0000,0.9340,0.8923,0.8533,0.8160,0.7801,0.7457,0.7127,0.6810,
          0.6507,0.6215],
    730: [1.0000,0.9298,0.8845,0.8419,0.8013,0.7625,0.7254,0.6900,0.6563,
          0.6240],
}


def get_soh_by_year(annual_cycles: float) -> list[float]:
    """
    给定年等效循环次数，按华为官方表线性插值，返回 year 0~25 的 SOH 列表。
    EoL 年份后的 SOH 强制为 0（已退役）。
    Interpolate Huawei SOH table for given annual_cycles → list[26] (year 0-25).
    """
    keys = sorted(HUAWEI_SOH_TABLE.keys())
    ac = float(max(min(annual_cycles, keys[-1]), keys[0]))

    if ac <= keys[0]:
        base = list(HUAWEI_SOH_TABLE[keys[0]])
    elif ac >= keys[-1]:
        base = list(HUAWEI_SOH_TABLE[keys[-1]])
    else:
        lo = max(k for k in keys if k <= ac)
        hi = min(k for k in keys if k >= ac)
        if lo == hi:
            base = list(HUAWEI_SOH_TABLE[lo])
        else:
            frac = (ac - lo) / (hi - lo)
            lo_a = HUAWEI_SOH_TABLE[lo]
            hi_a = HUAWEI_SOH_TABLE[hi]
            n = min(len(lo_a), len(hi_a))
            base = [lo_a[i] * (1 - frac) + hi_a[i] * frac for i in range(n)]

    # Pad to 26 entries (year 0-25); years beyond table = 0.0 (past EoL)
    result: list[float] = list(base)
    while len(result) < 26:
        result.append(0.0)

    # Zero out any year after EoL (SOH drops below threshold)
    eol_hit = False
    for i in range(1, len(result)):
        if eol_hit or result[i] < BESS_EOL_SOH:
            eol_hit = True
            result[i] = 0.0
    return result


def compute_bess_eol(throughput_yr1: float, bess_kwh: float,
                     cycles: int, dod: float) -> tuple[float, float]:
    """
    计算年等效循环次数 + EoL年份（基于华为官方 SOH 衰减表，EoL = SOH < 60%）
    Returns (eol_years, annual_cycles)
    """
    usable = bess_kwh * dod / 100.0
    if usable <= 0:
        return 25.0, 0.0
    annual_cycles = throughput_yr1 / (2.0 * usable)
    if annual_cycles <= 0:
        return 25.0, 0.0

    soh_arr = get_soh_by_year(annual_cycles)
    eol = 25.0
    for yr in range(1, len(soh_arr)):
        if soh_arr[yr] < BESS_EOL_SOH:
            prev = soh_arr[yr - 1]
            curr = soh_arr[yr]
            frac = (prev - BESS_EOL_SOH) / max(prev - curr, 1e-9)
            eol = round(yr - 1 + frac, 1)
            break
    return eol, round(annual_cycles, 2)

# Section 12B 加速折旧 / South Africa Section 12B accelerated depreciation
SECTION_12B = {1: 0.50, 2: 0.25, 3: 0.25}

ANALYSIS_YEARS = 25
FOREX_FALLBACK = 18.5   # USD/ZAR 后备汇率 / fallback rate

# C倍率选项 / C-rate options
C_RATE_OPTIONS = {"0.25C (4h)": 0.25, "0.5C (2h)": 0.50, "1C (1h)": 1.00}

# 默认参数 / Default parameters
DEFAULT_PARAMS = {
    "lat": -26.1,
    "lon": 28.0,
    "pv_kwp": 4000.0,              # 4 MWp
    "bess_kwh": 10000.0,           # 10 MWh
    "c_rate_label": "0.5C (2h)",
    "load_peak_kw": 2500.0,        # 高峰时段负载 kW
    "load_std_kw": 2500.0,         # 平期负载 kW
    "load_offpeak_kw": 500.0,      # 谷期（夜间）负载 kW
    "pv_loss": 14.0,
    "tilt": 26.0,                  # abs(lat) for SA
    "azimuth": 180.0,              # 南半球正北朝赤道 = 180° in PVGIS convention
    "rte": 88.2,
    "bess_cycles": 6000,
    "dod": 90.0,
    "forex_usd_zar": FOREX_FALLBACK,
    "pv_usd_per_w": 0.75,
    "bess_usd_per_wh": 0.20,
    "pv_opex_per_kwp": 125.0,
    "bess_opex_per_kwh": 10.0,
    "tariff_escalation": 6.5,
    "discount_rate": 10.0,
    "tax_rate": 27.0,
    "pv_degradation": 0.5,
    # 电价模式 / Tariff mode (see TARIFF_DB)
    "tariff_mode": "Megaflex ≤300km <500V",
    # 冬季高峰季 Jun-Aug / Winter HIGH season (Eskom Megaflex 2025/26 ≤300km <500V)
    "w_morning_peak": 8.1348,
    "w_evening_peak": 8.1348,
    "w_standard":     2.2302,
    "w_off_peak":     1.5740,
    # 夏季低谷季 Sep-May / Summer LOW season
    "s_morning_peak": 3.5294,
    "s_evening_peak": 3.5294,
    "s_standard":     2.0990,
    "s_off_peak":     1.5740,
}

# ─────────────────────────────────────────────────────────────
# Session State 初始化 / Session State Initialization
# ─────────────────────────────────────────────────────────────
def init_session_state():
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        for k, v in DEFAULT_PARAMS.items():
            st.session_state[k] = v
        st.session_state.stashed_params = None
        st.session_state.results = None
        st.session_state.hourly_df = None
        st.session_state.fin_df = None
        st.session_state.pvgis_status = "待获取 / Pending"
        st.session_state.annual_pv_kwh = None
        st.session_state.pvgis_key = ""      # 用于检测位置变化 / detect location change

init_session_state()

# ─────────────────────────────────────────────────────────────
# 工具函数 / Utility Functions
# ─────────────────────────────────────────────────────────────

def fetch_forex_rate() -> float:
    """实时获取 USD/ZAR 汇率（三路冗余）/ Live USD/ZAR rate with 3-tier fallback"""
    apis = [
        ("https://open.er-api.com/v6/latest/USD",         lambda r: r.json()["rates"]["ZAR"]),
        ("https://api.exchangerate-api.com/v4/latest/USD", lambda r: r.json()["rates"]["ZAR"]),
        ("https://api.frankfurter.app/latest?from=USD&to=ZAR",
         lambda r: r.json()["rates"]["ZAR"]),
    ]
    for url, extractor in apis:
        try:
            r = requests.get(url, timeout=6)
            r.raise_for_status()
            return float(extractor(r))
        except Exception:
            continue
    return FOREX_FALLBACK


@st.cache_data(ttl=3600)
def _fetch_forex_cached() -> float:
    """启动时自动拉取，缓存 1 小时避免频繁请求 / Auto-fetch on startup, cached 1h"""
    return fetch_forex_rate()


# 启动时自动拉取实时汇率（函数已定义，安全调用）
# Auto-fetch live forex rate on startup — functions are now defined, safe to call
if "forex_auto_fetched" not in st.session_state:
    st.session_state.forex_usd_zar = _fetch_forex_cached()
    st.session_state.forex_auto_fetched = True


def get_capex_zar() -> tuple[float, float]:
    """从USD造价和汇率计算ZAR单价 / Compute ZAR unit costs from USD and forex"""
    rate = st.session_state.forex_usd_zar
    pv_per_kwp   = st.session_state.pv_usd_per_w   * 1000.0 * rate  # $/W→ZAR/kWp
    bess_per_kwh = st.session_state.bess_usd_per_wh * 1000.0 * rate  # $/Wh→ZAR/kWh
    return pv_per_kwp, bess_per_kwh


def get_tariff_for_hour(hour: int, month: int, day_type: str = "weekday") -> tuple[float, str]:
    """
    SA Eskom 2025/26 TOU periods (Megaflex/Miniflex/Nightsave):
    Weekday: Morning peak 07:00-09:00, Evening peak 17:00-20:00 (Appendix A 2025/26 update)
    Saturday: off-peak all day
    Sunday/holidays: off-peak + new 2h standard 18:00-20:00 (Appendix A 2025/26)
    High season: June-August ONLY
    day_type: "weekday" | "saturday" | "sunday"
    """
    is_winter = month in WINTER_MONTHS
    pfx = "w_" if is_winter else "s_"

    off_peak_p = st.session_state[f"{pfx}off_peak"]
    morning_p  = st.session_state[f"{pfx}morning_peak"]
    evening_p  = st.session_state[f"{pfx}evening_peak"]
    standard_p = st.session_state[f"{pfx}standard"]

    if day_type == "sunday":
        # 2025/26: new 2h standard period on Sunday evening
        if 18 <= hour < 20:
            return standard_p, "standard"
        return off_peak_p, "off_peak"

    if day_type == "saturday":
        return off_peak_p, "off_peak"

    # weekday
    if hour < 6 or hour >= 22:     # 22:00-06:00 off-peak
        return off_peak_p, "off_peak"
    elif 7 <= hour < 9:            # 07:00-09:00 morning peak (2h, reduced from 3h)
        return morning_p, "morning_peak"
    elif 17 <= hour < 20:          # 17:00-20:00 evening peak (3h, extended from 2h)
        return evening_p, "evening_peak"
    else:
        return standard_p, "standard"


def get_pvgis_data(lat, lon, kwp, loss, tilt, azimuth) -> dict:
    """
    调用 PVGIS API / Call EU PVGIS API
    失败时自动按 1650h 经验值托底 / Auto fallback to 1650h empirical on failure
    """
    try:
        url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"
        params = {
            "lat": lat, "lon": lon,
            "peakpower": kwp, "loss": loss,
            "angle": tilt, "aspect": azimuth,
            "outputformat": "json",
            "pvtechchoice": "crystSi",
            "mountingplace": "free",
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        monthly = data["outputs"]["monthly"]["fixed"]
        annual_kwh = sum(m["E_m"] for m in monthly)
        return {
            "status": "API成功 / API Success ✓",
            "annual_kwh": annual_kwh,
            "winter_daily_kwh": monthly[6]["E_d"],   # July
            "summer_daily_kwh": monthly[0]["E_d"],   # January
            "monthly_kwh": [m["E_m"] for m in monthly],
        }
    except Exception as e:
        loss_f = 1 - loss / 100
        annual_kwh = 1650 * kwp * loss_f
        avg_d = annual_kwh / 365
        return {
            "status": f"离线托底 / Offline ({str(e)[:35]})",
            "annual_kwh": annual_kwh,
            "winter_daily_kwh": avg_d * 0.70,
            "summer_daily_kwh": avg_d * 1.30,
            "monthly_kwh": [annual_kwh / 12] * 12,
        }


def build_hourly_pv_profile(pvgis_data: dict, pv_kwp: float) -> np.ndarray:
    """
    月发电量 → 8760小时曲线，正态分布权重（06:00-18:00）
    Monthly generation → 8760h profile using Gaussian daytime weights
    """
    hours = np.arange(24)
    w = np.exp(-0.5 * ((hours - 12) / 2.5) ** 2)
    w[hours < 6] = 0.0
    w[hours > 18] = 0.0
    w /= w.sum()

    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    hourly_pv = np.zeros(8760)
    idx = 0
    for m_i, n_days in enumerate(days_in_month):
        daily = pvgis_data["monthly_kwh"][m_i] / n_days
        for _ in range(n_days):
            for h in range(24):
                hourly_pv[idx] = daily * w[h]
                idx += 1
    return hourly_pv


def run_8760_dispatch(
    pv_kwp: float,
    bess_kwh: float,
    bess_kw: float,
    load_peak_kw: float,       # kW during peak tariff hours
    load_std_kw: float,        # kW during standard hours
    load_offpeak_kw: float,    # kW during off-peak hours
    rte: float,
    dod: float,
    pvgis_data: dict,
    pv_degradation_pct: float = 0.0,
) -> dict:
    """
    ████████ 8760小时物理调度引擎 / 8760-Hour Physical Dispatch Engine ████████

    充电优先级 Charging Priority (strict order):
      1. 光伏余电 PV excess           → 始终接收，任何时段，免费
      2. 谷期电网 Off-peak grid       → 最小功率×最长时段，平摊8h谷期窗口（22-06h）
      3. 日间平期电网 Daytime std grid → 仅 09-16h，peak ≥ (std/RTE)×1.2 时允许
                                         最小功率×平摊剩余平期小时（09h→8h，16h→1h）
      4. 傍晚平期 Evening std 20-21h  → 【绝不充电】谷期 ≤2h 后开始，等待更便宜电价
      5. 高峰电网 Peak grid           → 【禁止】绝不在高峰时段从电网充电

    放电优先级 Discharge Priority:
      高峰时段全力放电 → 平期/谷期保留 SOC，不放电

    最小功率原则 Min-Power Principle:
      功率 = min(bess_kw, need / remaining_hours / RTE)
      → 谷期：need / op_hrs_left（最多8h），功率天然最低
      → 日间平期：need / (17-h)，09h时最多8h，逐时收敛
      → 上限始终为用户设定 bess_kw（配置 C 率为硬上限，任何时段不超过）

    收益最大化 Revenue-First Logic:
      充电总是选最便宜电价：谷期(off_peak) < 日间平期(standard) < 傍晚平期(等谷期)
      傍晚平期（20-21h）距谷期仅 ≤2h，主动等待更便宜谷期，确保套利收益最大

    平期充电经济门槛:
      peak_price ≥ (standard_price / RTE) × 1.2
      → Megaflex/Miniflex TOU 冬/夏均满足，允许日间补充充电
      → Nightsave / PPA 平价电率：不满足，自动禁用

    物理约束:
      - SOC 充电增量 = 充入电量 × RTE（充电损耗计入 RTE）
      - SOC 放电减量 = 放出电量（放电直接减 SOC）
    """
    rte_dec   = rte / 100.0
    dod_dec   = dod / 100.0
    usable    = bess_kwh * dod_dec

    load_map = {
        "morning_peak": load_peak_kw,
        "evening_peak": load_peak_kw,
        "standard":     load_std_kw,
        "off_peak":     load_offpeak_kw,
    }

    hourly_pv = build_hourly_pv_profile(pvgis_data, pv_kwp)
    hourly_pv *= (1 - pv_degradation_pct / 100.0)

    soc = usable * 0.5
    tot_throughput = 0.0
    records = []

    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    g = 0  # global hour index

    for m_i, n_days in enumerate(days_in_month):
        month = m_i + 1
        for d in range(n_days):
            # 计算当天类型 / Determine day type using 2025 calendar
            cal_date = _date(2025, month, d + 1)
            wday = cal_date.weekday()  # 0=Mon, 5=Sat, 6=Sun
            if cal_date in SA_PUBLIC_HOLIDAYS_2025:
                day_type = "sunday"    # holidays treated as Sunday per Appendix D
            elif wday == 5:
                day_type = "saturday"
            elif wday == 6:
                day_type = "sunday"
            else:
                day_type = "weekday"

            for h in range(24):
                tariff_price, period = get_tariff_for_hour(h, month, day_type)
                pv_gen  = hourly_pv[g]
                load    = load_map[period]

                pv_to_load   = min(pv_gen, load)
                pv_excess    = pv_gen - pv_to_load
                net_load     = load - pv_to_load

                charge_pv    = 0.0
                charge_grid  = 0.0
                discharge    = 0.0

                # ── 季节感知的峰期价格 / Season-aware peak & off-peak prices
                pfx = "w_" if month in WINTER_MONTHS else "s_"
                season_peak  = max(
                    st.session_state[f"{pfx}morning_peak"],
                    st.session_state[f"{pfx}evening_peak"],
                )
                off_peak_p   = st.session_state[f"{pfx}off_peak"]
                standard_p   = st.session_state[f"{pfx}standard"]

                # ── 经济护栏 / Economic guards ─────────────────────────────
                # 夜间电网充电需要: peak > off_peak（否则无套利空间）
                # Night grid-charge only if peak tariff beats off-peak
                grid_charge_viable = season_peak > off_peak_p

                # 高峰放电需要: 当前 tariff > off_peak（否则放电亏本）
                # Peak discharge only if this hour's rate exceeds off-peak
                # (Economic break-even including RTE: tariff_price * rte_dec > off_peak_p)
                discharge_viable = tariff_price > off_peak_p

                if period in ("morning_peak", "evening_peak"):
                    # 削峰放电（仅当该时段电价高于谷价时才有套利价值）
                    if discharge_viable:
                        dis = min(bess_kw, soc, net_load)
                        discharge = max(0.0, dis)
                        soc      -= discharge
                        net_load -= discharge

                    # 余电充电（光伏免费，始终接收）
                    if pv_excess > 0 and soc < usable:
                        space = usable - soc
                        c = min(pv_excess, space / rte_dec, bess_kw)
                        charge_pv = c
                        soc += c * rte_dec
                        tot_throughput += c * rte_dec

                elif period == "off_peak":
                    # ── 1. 光伏余电优先（免费，始终接收）
                    if pv_excess > 0 and soc < usable:
                        space = usable - soc
                        c = min(pv_excess, space / rte_dec, bess_kw)
                        charge_pv = c
                        soc += c * rte_dec
                        tot_throughput += c * rte_dec

                    # ── 2. 电网充电：最小功率 × 最长时段
                    # 公式：c = min(bess_kw, need / op_hrs_left / RTE)
                    # 谷期窗口 22:00-06:00（共 8h），每小时自动计算最低所需功率
                    # 结果：恒功率充满整个窗口，不在短时间内高功率冲满
                    # 上限：用户设定的 bess_kw（配置 C 率为硬上限，任何时段不超过）
                    # Grid charge at minimum power spread over remaining off-peak window:
                    #   c = min(bess_kw, need / op_hrs_left / RTE)
                    # This naturally keeps power constant and as low as possible.
                    if grid_charge_viable and soc < usable:
                        # 22:00-06:00 窗口内含当前小时的剩余小时数
                        # max(1,...) 防止 h=6 周六/超大电池低C率场景除零
                        op_hrs_left = max(1, ((24 - h) + 6) if h >= 22 else (6 - h))
                        need = usable - soc
                        c = min(bess_kw, need / op_hrs_left / rte_dec)
                        if c > 0.01:
                            charge_grid = c
                            soc += c * rte_dec
                            tot_throughput += c * rte_dec

                else:  # standard 平期
                    # ── 1. 光伏余电优先（免费，始终接收）
                    if pv_excess > 0 and soc < usable:
                        space = usable - soc
                        c = min(pv_excess, space / rte_dec, bess_kw)
                        charge_pv = c
                        soc += c * rte_dec
                        tot_throughput += c * rte_dec

                    # ── 2. 电网充电：仅日间平期 09:00-16:59，经济门槛 + 最小功率
                    # 【收益最大化原则】傍晚平期（20-21h）绝不从电网充电：
                    #   谷期在 ≤2h 后开始（22:00），谷期电价比平期便宜 ~29%
                    #   等待谷期充电始终更经济 → 20-21h 不充，等 22h 谷期
                    # 日间平期（09-16h）允许补充充电：
                    #   经济条件：peak ≥ (std/RTE) × 1.2（Megaflex 冬/夏均满足）
                    #   功率：min(bess_kw, need / hrs_remaining / RTE)
                    #   → 最低恒功率平摊到 17:00 前；上限为用户设定 bess_kw
                    # Grid charge ONLY during daytime standard (09:00-16:59).
                    # Evening standard (20-21h): NEVER charge — off-peak starts ≤2h later
                    # at ~29% lower cost. Revenue-maximising rule: always wait for cheapest.
                    # Power = min(bess_kw, need / hrs_remaining / RTE) — min-power spread.
                    std_effective_cost = tariff_price / rte_dec
                    if (grid_charge_viable
                            and season_peak >= std_effective_cost * 1.2
                            and soc < usable
                            and 9 <= h < 17):            # 日间平期专用，傍晚平期排除
                        hrs_left = 17 - h                # 09h→8h，10h→7h … 16h→1h
                        need = usable - soc
                        c = min(bess_kw, need / hrs_left / rte_dec)
                        if c > 0.01:
                            charge_grid = c
                            soc += c * rte_dec
                            tot_throughput += c * rte_dec

                    # 平期不放电——保留 SOC 给高峰 / No discharge; preserve SOC for peaks
                    # discharge remains 0

                # 放电累加吞吐量
                if discharge > 0:
                    tot_throughput += discharge

                soc = np.clip(soc, 0.0, usable)

                grid_buy = max(0.0, net_load)

                # 节省计算（季节因子已内含于 tariff_price）
                pv_saving   = pv_to_load * tariff_price
                dis_saving  = discharge * tariff_price

                # 谷期用原始谷价×季节因子计算充电成本；其他时段 tariff_price 已含季节
                if period == "off_peak":
                    grid_charge_cost = charge_grid * st.session_state[f"{pfx}off_peak"]
                else:
                    grid_charge_cost = charge_grid * tariff_price

                net_saving = pv_saving + dis_saving - grid_charge_cost

                records.append({
                    "hour": g, "month": month, "day": d + 1, "hour_of_day": h,
                    "period": period,
                    "tariff_ZAR_kWh": round(tariff_price, 4),
                    "load_kWh": round(load, 4),
                    "pv_gen_kWh": round(pv_gen, 4),
                    "pv_to_load_kWh": round(pv_to_load, 4),
                    "pv_excess_kWh": round(pv_excess, 4),
                    "charge_pv_kWh": round(charge_pv, 4),
                    "charge_grid_kWh": round(charge_grid, 4),
                    "discharge_kWh": round(discharge, 4),
                    "soc_kWh": round(soc, 4),
                    "soc_pct": round(soc / usable * 100, 1) if usable > 0 else 0.0,
                    "grid_buy_kWh": round(grid_buy, 4),
                    "pv_saving_ZAR": round(pv_saving, 4),
                    "bess_net_saving_ZAR": round(dis_saving - grid_charge_cost, 4),
                    "net_saving_ZAR": round(net_saving, 4),
                })
                g += 1

    df = pd.DataFrame(records)
    return {
        "annual_saving_ZAR":      df["net_saving_ZAR"].sum(),
        "annual_pv_saving_ZAR":   df["pv_saving_ZAR"].sum(),
        "annual_bess_saving_ZAR": df["bess_net_saving_ZAR"].sum(),
        "annual_pv_gen_kWh":      df["pv_gen_kWh"].sum(),
        "annual_load_kWh":        df["load_kWh"].sum(),
        "tot_throughput_kWh":     tot_throughput,
        "annual_grid_charge_kWh": df["charge_grid_kWh"].sum(),
        "annual_pv_charge_kWh":   df["charge_pv_kWh"].sum(),
        "annual_discharge_kWh":   df["discharge_kWh"].sum(),
        "annual_grid_buy_kWh":    df["grid_buy_kWh"].sum(),
        "hourly_df": df,
    }


def compute_bess_eol(throughput_yr1: float, bess_kwh: float,
                     cycles: int, dod: float) -> tuple[float, float]:
    """计算 BESS 物理退役年份和年等效循环次数 / Compute BESS EoL and annual cycles"""
    usable = bess_kwh * dod / 100.0
    if usable <= 0:
        return 999.0, 0.0
    annual_cycles = throughput_yr1 / (2.0 * usable)
    if annual_cycles <= 0:
        return 999.0, 0.0
    return round(cycles / annual_cycles, 2), round(annual_cycles, 2)


def run_25yr_financial_model(
    dispatch_yr1: dict,
    pv_kwp: float,
    bess_kwh: float,
    eol_years: float,
    params: dict,
    annual_cycles: float = 365.0,
) -> pd.DataFrame:
    """
    25年逐年财务模型（含 Section 12B、SOH 衰减、EoL 断崖）
    SOH 来自华为官方 LUNA2000-2236-1S 衰减表，按年等效循环次数插值
    PV 节省仅受光衰影响；BESS 节省受 SOH 影响；SOH < 60% 后 BESS 归零
    """
    pv_capex   = pv_kwp   * params["pv_capex_per_kwp"]
    bess_capex = bess_kwh * params["bess_capex_per_kwh"]
    total_capex = pv_capex + bess_capex

    esc  = params["tariff_escalation"] / 100.0
    disc = params["discount_rate"] / 100.0
    tax  = params["tax_rate"] / 100.0
    deg  = params["pv_degradation"] / 100.0

    base_pv_save   = dispatch_yr1["annual_pv_saving_ZAR"]
    base_bess_save = dispatch_yr1["annual_bess_saving_ZAR"]

    # 按实际年循环次数取华为官方 SOH 曲线 / Official SOH curve at actual cycle rate
    soh_arr = get_soh_by_year(annual_cycles)

    rows = []
    cum_cf = -total_capex

    for yr in range(1, ANALYSIS_YEARS + 1):
        esc_mult  = (1 + esc) ** (yr - 1)
        deg_mult  = (1 - deg) ** (yr - 1)

        # SOH from official table (0.0 after EoL, i.e. SOH < 60%)
        soh = soh_arr[yr] if yr < len(soh_arr) else 0.0
        bess_alive = soh >= BESS_EOL_SOH

        # 精准分项节省（PV 节省不受 SOH 影响）
        pv_save   = base_pv_save   * esc_mult * deg_mult
        bess_save = base_bess_save * esc_mult * soh     # EoL后soh=0自动断崖
        saving    = pv_save + bess_save

        # 运维费用
        pv_opex   = pv_kwp   * params["pv_opex_per_kwp"]   * (1 + esc * 0.5) ** (yr - 1)
        bess_opex = (bess_kwh * params["bess_opex_per_kwh"] * (1 + esc * 0.5) ** (yr - 1)
                     if bess_alive else 0.0)
        total_opex = pv_opex + bess_opex

        ebitda = saving - total_opex

        # Section 12B 折旧
        depreciation = total_capex * SECTION_12B.get(yr, 0.0)
        tax_shield   = depreciation * tax   # 仅用于报表展示

        ebit = ebitda - depreciation
        # net_cf 只扣实缴税：折旧节税已内含于 EBIT→更低税额，不可重复加 tax_shield
        cash_tax = max(0.0, ebit * tax)
        net_profit = ebit - cash_tax
        net_cf   = ebitda - cash_tax       # 折旧是非现金项，EBITDA - 税
        pv_cf    = net_cf / (1 + disc) ** yr

        cum_cf += net_cf

        rows.append({
            "年份 Year": yr,
            "BESS": "✓" if bess_alive else "✗ EoL",
            "SOH%": round(soh * 100, 1),
            "节省 Saving (ZAR)": round(saving, 0),
            "PV节省": round(pv_save, 0),
            "BESS套利": round(bess_save, 0),
            "PV O&M (ZAR)": round(pv_opex, 0),
            "BESS O&M (ZAR)": round(bess_opex, 0),
            "EBITDA (ZAR)": round(ebitda, 0),
            "12B折旧 (ZAR)": round(depreciation, 0),
            "Tax Shield (ZAR)": round(tax_shield, 0),
            "净利润 (ZAR)": round(net_profit, 0),
            "净现金流 NCF (ZAR)": round(net_cf, 0),
            "折现CF PV (ZAR)": round(pv_cf, 0),
            "累计CF (ZAR)": round(cum_cf, 0),
        })

    return pd.DataFrame(rows)


def compute_npv_irr(fin_df: pd.DataFrame, total_capex: float,
                    discount_rate: float) -> tuple[float, float]:
    """计算 NPV 和 IRR（二分法）/ Compute NPV and IRR via bisection"""
    cfs = [-total_capex] + fin_df["净现金流 NCF (ZAR)"].tolist()
    dr = discount_rate / 100.0
    npv = sum(cf / (1 + dr) ** t for t, cf in enumerate(cfs))

    try:
        lo, hi = -0.5, 5.0
        irr = 0.0
        for _ in range(120):
            mid = (lo + hi) / 2
            pv = sum(cf / (1 + mid) ** t for t, cf in enumerate(cfs))
            if abs(pv) < 0.5:
                irr = mid
                break
            if pv > 0:
                lo = mid
            else:
                hi = mid
        irr = mid * 100
    except Exception:
        irr = 0.0

    return round(npv, 0), round(irr, 2)


# ─────────────────────────────────────────────────────────────
# 自动 PVGIS 联动 / Auto-PVGIS on location/capacity change
# ─────────────────────────────────────────────────────────────
def check_auto_pvgis():
    """当经纬度或光伏容量变化时自动拉取 PVGIS / Auto-fetch PVGIS when location or PV changes"""
    if st.session_state.pv_kwp <= 0:
        return
    # 用位置+容量+角度作唯一键检测变化 / Use location+capacity+angles as change key
    key = (f"{st.session_state.lat:.3f}_{st.session_state.lon:.3f}"
           f"_{st.session_state.pv_kwp:.0f}_{st.session_state.pv_loss:.1f}"
           f"_{st.session_state.tilt:.1f}_{st.session_state.azimuth:.1f}")
    if st.session_state.pvgis_key != key:
        result = get_pvgis_data(
            st.session_state.lat, st.session_state.lon,
            st.session_state.pv_kwp, st.session_state.pv_loss,
            st.session_state.tilt, st.session_state.azimuth,
        )
        st.session_state.pvgis_data  = result
        st.session_state.pvgis_status = result["status"]
        st.session_state.annual_pv_kwh = result["annual_kwh"]
        st.session_state.pvgis_key   = key


# ─────────────────────────────────────────────────────────────
# Excel 专业报告生成器 / Professional Excel Report Generator
# 6 sheets: Cover · Parameters · 25Y Model · Monthly · Charts · Raw Data
# ─────────────────────────────────────────────────────────────
def generate_excel_report() -> bytes:
    """
    生成 6-sheet 专业级 Excel 报告（session_state 快照，不重新计算）
    Sheet 3 使用工作表内绝对引用（$B$5 等），确保 Excel 公式正常运算。
    Returns raw bytes for st.download_button.
    """
    import datetime as _dt
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, LineChart, Reference

    # ── Session-state snapshot ────────────────────────────────
    ss      = st.session_state
    res     = ss.results
    fin_df  = ss.fin_df
    h_df    = ss.hourly_df
    d1      = res["dispatch_yr1"]
    pvg     = res["pvgis_data"]
    soh_arr = get_soh_by_year(res["annual_cycles"])
    pv_zar, bess_zar = get_capex_zar()
    bess_zero = (ss.bess_kwh == 0)   # flag: hide BESS charts/columns when no BESS

    # ── Colour palette ────────────────────────────────────────
    C_NAVY   = "1F3864"
    C_DARK   = "2E4057"
    C_MID    = "2E5F8A"
    C_LTBLUE = "D6E4F0"
    C_LOCKED = "FFF9C4"
    C_ALT    = "F2F6FC"
    C_GREEN  = "196F3D"
    C_RED    = "922B21"

    _thin = Side(style="thin", color="BDBDBD")

    def _fill(hex_c):
        return PatternFill("solid", fgColor=hex_c)

    def _font(bold=False, sz=10, color="1A1A2E", italic=False):
        return Font(name="Calibri", size=sz, bold=bold, color=color, italic=italic)

    def _align(h="left", v="center", wrap=False):
        return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

    def _bdr():
        return Border(left=_thin, right=_thin, top=_thin, bottom=_thin)

    wb = Workbook()

    # ════════════════════════════════════════════════════════════
    # SHEET 1 — 封面 Cover
    # ════════════════════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = "封面 Cover"
    ws1.sheet_view.showGridLines = False
    for ci, w in enumerate([2, 28, 20, 20, 20, 20, 2], 1):
        ws1.column_dimensions[get_column_letter(ci)].width = w

    # Title banner
    ws1.merge_cells("B2:G2")
    c = ws1["B2"]
    c.value = "BTM 光储财务测算报告  /  BTM PV+BESS Financial Feasibility Report"
    c.font = Font("Calibri", size=16, bold=True, color="FFFFFF")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws1.row_dimensions[2].height = 42

    ws1.merge_cells("B3:G3")
    c = ws1["B3"]
    c.value = "Powered by Huawei SA Digital Power  ·  South Africa C&I BTM Solar + Storage"
    c.font = Font("Calibri", size=9, color="D6E4F0")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws1.row_dimensions[3].height = 16

    # Project overview header
    ws1.merge_cells("B5:G5")
    c = ws1["B5"]
    c.value = "  项目概览 / Project Overview"
    c.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    c.fill = _fill(C_DARK); c.alignment = _align("left")
    ws1.row_dimensions[5].height = 20

    payback_str = f"{res['payback']:.2f} yr" if res['payback'] else "25yr+"
    info_rows = [
        ("地点 Location",             f"Lat {ss.lat:.3f}°  /  Lon {ss.lon:.3f}°"),
        ("系统规模 System Size",       f"PV  {ss.pv_kwp:,.0f} kWp  +  BESS  {ss.bess_kwh:,.0f} kWh"),
        ("电价模式 Tariff Mode",       ss.get("tariff_mode", "—")),
        ("汇率 Forex Rate",            f"1 USD = {ss.forex_usd_zar:.2f} ZAR"),
        ("电价增速 Tariff Escalation", f"{ss.tariff_escalation:.1f}% / yr"),
        ("折现率 Discount Rate",       f"{ss.discount_rate:.1f}%"),
        ("PVGIS 年发电量 PV Gen",      f"{pvg.get('annual_kwh', 0):,.0f} kWh/yr"),
        ("导出时间 Export Time",        _dt.datetime.now().strftime("%Y-%m-%d  %H:%M")),
    ]
    for i, (lbl, val) in enumerate(info_rows):
        r = 6 + i
        ws1.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        cl = ws1.cell(row=r, column=2, value=lbl)
        cl.font = _font(bold=True, sz=10); cl.fill = _fill(C_LTBLUE)
        cl.alignment = _align(); cl.border = _bdr()
        ws1.merge_cells(start_row=r, start_column=4, end_row=r, end_column=6)
        cv = ws1.cell(row=r, column=4, value=val)
        cv.font = _font(sz=10); cv.fill = _fill("FFFFFF")
        cv.alignment = _align(); cv.border = _bdr()
        ws1.row_dimensions[r].height = 18

    # KPI section header
    ws1.merge_cells("B15:G15")
    c = ws1["B15"]
    c.value = "  关键财务指标 / Key Financial Metrics"
    c.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    c.fill = _fill(C_DARK); c.alignment = _align("left")
    ws1.row_dimensions[15].height = 20

    kpis = [
        ("总投资 CAPEX",       f"R {res['total_capex']/1e6:.2f} M",      "ZAR"),
        ("净现值 NPV 25yr",    f"R {res['npv']/1e6:.2f} M",              "ZAR"),
        ("内部回报率 IRR",      f"{res['irr']:.2f}%",                     "Project IRR"),
        ("回收期 Payback",     payback_str,                              "Simple Payback"),
        ("年1节省 Yr1 Save",   f"R {d1['annual_saving_ZAR']/1e6:.2f} M", "ZAR/yr"),
        ("BESS寿命 EoL",       f"Year {res['eol_years']:.1f}",           "SOH < 60%"),
    ]
    # 3 cols × 2 rows layout
    kpi_layout = [
        ((16, 17), (2, 3)), ((16, 17), (4, 5)), ((16, 17), (6, 6)),
        ((19, 20), (2, 3)), ((19, 20), (4, 5)), ((19, 20), (6, 6)),
    ]
    for idx, ((r_top, r_bot), (c_l, c_r)) in enumerate(kpi_layout):
        if idx >= len(kpis):
            break
        lbl_k, val_k, _ = kpis[idx]
        for r_ in (r_top, r_bot):
            if c_l != c_r:
                ws1.merge_cells(start_row=r_, start_column=c_l,
                                end_row=r_, end_column=c_r)
            ws1.row_dimensions[r_].height = 22 if r_ == r_top else 26
        cl_k = ws1.cell(row=r_top, column=c_l, value=lbl_k)
        cl_k.font = _font(sz=8, bold=True, color="555555")
        cl_k.fill = _fill(C_LTBLUE); cl_k.alignment = _align("center"); cl_k.border = _bdr()
        cv_k = ws1.cell(row=r_bot, column=c_l, value=val_k)
        kpi_color = (C_GREEN if res["npv"] > 0 else C_RED) if idx == 1 else C_NAVY
        cv_k.font = Font("Calibri", size=13, bold=True, color=kpi_color)
        cv_k.fill = _fill(C_LTBLUE); cv_k.alignment = _align("center"); cv_k.border = _bdr()
    ws1.row_dimensions[18].height = 6  # gap row

    # Instructions
    ws1.merge_cells("B22:G22")
    c = ws1["B22"]
    c.value = "  使用说明 / Instructions"
    c.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    c.fill = _fill(C_MID); c.alignment = _align("left")
    ws1.row_dimensions[22].height = 20

    notes_text = (
        "● Yellow cells are locked export snapshots (PVGIS / dispatch results) — do not edit  /  黄色单元格为锁定快照，请勿修改\n"
        "● Green cells in Sheet 3 Row 4 are editable — all financial formulas recalculate automatically  /  Sheet3 第4行绿色单元格可调，公式自动更新\n"
        "● Charts (Sheet 5) are linked to Sheet 3 & 4 — they update automatically when you change parameters  /  图表与数据联动\n"
        "● Sheet 6 is a static 8,760-hour dispatch snapshot — it does not update with parameter changes  /  Sheet6 为原始调度数据快照\n"
        "● Adjustable: tariff escalation, discount rate, tax rate, PV/BESS unit costs, O&M rates  /  可调项：电价增速、折现率、税率、造价、运维费"
    )
    ws1.merge_cells("B23:G26")
    cn = ws1.cell(row=23, column=2, value=notes_text)
    cn.font = Font("Calibri", size=9, color="444444")
    cn.alignment = Alignment(wrap_text=True, vertical="top")
    cn.fill = _fill("F9F9F9"); cn.border = _bdr()
    for r_ in range(23, 27):
        ws1.row_dimensions[r_].height = 15

    # ════════════════════════════════════════════════════════════
    # SHEET 2 — 参数 Parameters
    # ════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("参数 Parameters")
    ws2.sheet_view.showGridLines = False
    for ci, w in enumerate([3, 34, 18, 14, 30], 1):
        ws2.column_dimensions[get_column_letter(ci)].width = w

    ws2.merge_cells("B1:E1")
    c = ws2.cell(row=1, column=2,
                 value="参数设置 / Parameters  ——  白色可调 · 黄色已锁定")
    c.font = Font("Calibri", size=12, bold=True, color="FFFFFF")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws2.row_dimensions[1].height = 30

    def _p_sec(r, title, bg=C_DARK):
        ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        c_ = ws2.cell(row=r, column=1, value=title)
        c_.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
        c_.fill = _fill(bg); c_.alignment = _align("left")
        ws2.row_dimensions[r].height = 18

    def _p_row(r, label, value, unit="", locked=False, fmt=None, formula=None):
        lk = ws2.cell(row=r, column=1, value="🔒" if locked else "")
        lk.font = _font(sz=9); lk.alignment = _align("center")
        lb = ws2.cell(row=r, column=2, value=label)
        lb.font = _font(sz=10); lb.fill = _fill(C_ALT)
        lb.alignment = _align(); lb.border = _bdr()
        vc = ws2.cell(row=r, column=3, value=(formula if formula else value))
        vc.fill = _fill(C_LOCKED if locked else "FFFFFF")
        vc.alignment = _align("center"); vc.border = _bdr()
        if fmt:
            vc.number_format = fmt
        un = ws2.cell(row=r, column=4, value=unit)
        un.font = _font(sz=9, italic=True, color="666666")
        un.fill = _fill(C_ALT); un.alignment = _align(); un.border = _bdr()
        ws2.row_dimensions[r].height = 17
        return vc

    # ── System Parameters (rows 3-12) ─────────────────────────
    _p_sec(3, "▌ 系统参数 / System Parameters")
    _p_row(4,  "光伏容量 PV Capacity",          ss.pv_kwp,           "kWp",        fmt="#,##0.0")
    _p_row(5,  "储能容量 BESS Capacity",         ss.bess_kwh,         "kWh",        fmt="#,##0.0")
    _p_row(6,  "C倍率 C-rate",                  ss.c_rate_label,     "—")
    _p_row(7,  "往返效率 RTE",                   ss.rte,              "%",          fmt="0.0")
    _p_row(8,  "放电深度 DoD",                   ss.dod,              "%",          fmt="0.0")
    _p_row(9,  "PV 年衰减率 PV Degradation",     ss.pv_degradation,   "%/yr",       fmt="0.00")
    _p_row(10, "光伏倾角 Tilt",                 ss.tilt,             "°",          fmt="0.0")
    _p_row(11, "方位角 Azimuth",               ss.azimuth,          "° (180=N)",  fmt="0.0")

    # ── Load Parameters (rows 13-17) ──────────────────────────
    _p_sec(13, "▌ 负载参数 / Load Profile")
    _p_row(14, "高峰负载 Peak Load",              ss.load_peak_kw,     "kW",         fmt="#,##0.0")
    _p_row(15, "平期负载 Standard Load",           ss.load_std_kw,      "kW",         fmt="#,##0.0")
    _p_row(16, "谷期负载 Off-peak Load",           ss.load_offpeak_kw,  "kW",         fmt="#,##0.0")

    # ── CAPEX & Forex (rows 18-25) ─────────────────────────────
    _p_sec(18, "▌ 投资造价 / CAPEX & Forex")
    _p_row(19, "光伏单价 PV Cost",               ss.pv_usd_per_w,     "USD/W",      fmt="0.000")
    _p_row(20, "储能单价 BESS Cost",              ss.bess_usd_per_wh,  "USD/Wh",     fmt="0.000")
    _p_row(21, "汇率 Forex Rate",               ss.forex_usd_zar,    "USD/ZAR",    fmt="0.00")
    _p_row(22, "PV 造价 ZAR/kWp",               pv_zar,              "ZAR/kWp",    fmt="#,##0.00",
           formula="=C19*1000*C21")
    _p_row(23, "BESS 造价 ZAR/kWh",             bess_zar,            "ZAR/kWh",    fmt="#,##0.00",
           formula="=C20*1000*C21")
    _p_row(24, "总投资 Total CAPEX",             res["total_capex"],  "ZAR",        fmt="#,##0",
           formula="=C4*C22+C5*C23")

    # ── OPEX (rows 26-29) ─────────────────────────────────────
    _p_sec(26, "▌ 运维费用 / OPEX")
    _p_row(27, "PV 运维 PV O&M",                ss.pv_opex_per_kwp,   "ZAR/kWp/yr", fmt="0.00")
    _p_row(28, "BESS 运维 BESS O&M",            ss.bess_opex_per_kwh, "ZAR/kWh/yr", fmt="0.00")

    # ── Financial Assumptions (rows 30-34) ────────────────────
    _p_sec(30, "▌ 财务假设 / Financial Assumptions")
    _p_row(31, "电费增速 Tariff Escalation",      ss.tariff_escalation, "%/yr",        fmt="0.0")
    _p_row(32, "折现率 Discount Rate",            ss.discount_rate,     "%",           fmt="0.0")
    _p_row(33, "企业税率 Corp Tax Rate",           ss.tax_rate,          "%",           fmt="0.0")

    # ── Tariff Rates (rows 35-43) ─────────────────────────────
    _p_sec(35, "▌ 电价 / Tariff Rates (ZAR/kWh incl VAT)")
    _p_row(36, "电价模式 Tariff Mode",             ss.get("tariff_mode", "—"), "—", locked=True)
    _p_row(37, "冬季高峰 Winter Peak",             ss.get("w_morning_peak", 0), "ZAR/kWh", fmt="0.0000")
    _p_row(38, "冬季平期 Winter Std",              ss.get("w_standard", 0),    "ZAR/kWh",  fmt="0.0000")
    _p_row(39, "冬季谷期 Winter Off-peak",         ss.get("w_off_peak", 0),    "ZAR/kWh",  fmt="0.0000")
    _p_row(40, "夏季高峰 Summer Peak",             ss.get("s_morning_peak", 0),"ZAR/kWh",  fmt="0.0000")
    _p_row(41, "夏季平期 Summer Std",              ss.get("s_standard", 0),    "ZAR/kWh",  fmt="0.0000")
    _p_row(42, "夏季谷期 Summer Off-peak",         ss.get("s_off_peak", 0),    "ZAR/kWh",  fmt="0.0000")

    # ── PVGIS Data LOCKED (rows 44-60) ────────────────────────
    _p_sec(44, "▌ PVGIS 数据（锁定 LOCKED — 导出时快照）", bg=C_MID)
    monthly_kwh = pvg.get("monthly_kwh", [0] * 12)
    _p_row(45, "纬度 Latitude",       ss.lat,                     "°",       locked=True, fmt="0.000")
    _p_row(46, "经度 Longitude",      ss.lon,                     "°",       locked=True, fmt="0.000")
    _p_row(47, "年发电量 Annual PV",  pvg.get("annual_kwh", 0),   "kWh/yr",  locked=True, fmt="#,##0")
    for mi, mn in enumerate(["Jan","Feb","Mar","Apr","May","Jun",
                              "Jul","Aug","Sep","Oct","Nov","Dec"]):
        val_m = monthly_kwh[mi] if mi < len(monthly_kwh) else 0
        _p_row(48 + mi, f"{mn} 发电量 PV Gen", val_m, "kWh",
               locked=True, fmt="#,##0")

    # ── Dispatch Results LOCKED (rows 61-66) ──────────────────
    _p_sec(61, "▌ Yr1 Dispatch Results / 年1调度结果 (Locked)", bg=C_MID)
    _p_row(62, "年1 PV 节省 Yr1 PV Saving",    d1["annual_pv_saving_ZAR"],   "ZAR/yr", locked=True, fmt="#,##0")
    _p_row(63, "年1 BESS 节省 Yr1 BESS Save",  d1["annual_bess_saving_ZAR"], "ZAR/yr", locked=True, fmt="#,##0")
    _p_row(64, "年等效循环 Annual Cycles",       res["annual_cycles"],          "/yr",    locked=True, fmt="0.00")
    _p_row(65, "BESS 寿命 BESS EoL",           res["eol_years"],              "years",  locked=True, fmt="0.0")

    # ── SOH Table LOCKED (rows 67-93) ─────────────────────────
    _p_sec(67, "▌ BESS SOH Degradation Table — Huawei LUNA2000-2236-1S (Locked)", bg=C_MID)
    for ci_h, hdr_h in enumerate(["年份 Year", "SOH (%)", "状态 Status"], start=2):
        hc = ws2.cell(row=68, column=ci_h, value=hdr_h)
        hc.font = _font(bold=True, sz=9, color="FFFFFF")
        hc.fill = _fill(C_DARK); hc.alignment = _align("center"); hc.border = _bdr()
    ws2.row_dimensions[68].height = 15
    for yr_i in range(1, 26):          # years 1..25 → Parameters rows 69..93
        sr = 68 + yr_i
        sv = soh_arr[yr_i] if yr_i < len(soh_arr) else 0.0
        alive_s = sv >= BESS_EOL_SOH
        yc = ws2.cell(row=sr, column=2, value=yr_i)
        yc.font = _font(sz=9); yc.fill = _fill(C_LOCKED)
        yc.alignment = _align("center"); yc.border = _bdr()
        sc = ws2.cell(row=sr, column=3, value=round(sv * 100, 2))
        sc.font = _font(sz=9, color=C_GREEN if alive_s else C_RED)
        sc.fill = _fill(C_LOCKED); sc.alignment = _align("center")
        sc.number_format = "0.00"; sc.border = _bdr()
        stc = ws2.cell(row=sr, column=4, value="✓ Active" if alive_s else "✗ EoL")
        stc.font = _font(sz=9, bold=True, color=C_GREEN if alive_s else C_RED)
        stc.fill = _fill(C_LOCKED); stc.alignment = _align("center"); stc.border = _bdr()
        ws2.row_dimensions[sr].height = 15

    # ════════════════════════════════════════════════════════════
    # SHEET 3 — 财务模型 25Y Model
    # 所有公式使用工作表内绝对引用（$B$5 等），不跨表，确保 Excel 正常计算
    # ════════════════════════════════════════════════════════════
    ws3 = wb.create_sheet("财务模型 25Y Model")
    ws3.sheet_view.showGridLines = False
    ws3.freeze_panes = "A8"    # freeze title + param section + header
    for ci, w in enumerate([6,14,10,14,14,14,12,12,14,13,12,12,12,14,13,14,12], 1):
        ws3.column_dimensions[get_column_letter(ci)].width = w

    # ── Title row 1 ───────────────────────────────────────────
    ws3.merge_cells("A1:Q1")
    c = ws3.cell(row=1, column=1,
                 value="25-Year Financial Model / 25年财务模型  "
                       "—  Edit green cells in Row 4 · All formulas auto-recalculate / 修改第4行绿色单元格，公式自动更新")
    c.font = Font("Calibri", size=12, bold=True, color="FFFFFF")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws3.row_dimensions[1].height = 28

    # ── Parameter Section header row 2 ───────────────────────
    ws3.merge_cells("A2:Q2")
    c = ws3.cell(row=2, column=1,
                 value="⚙️  Adjustable Parameters / 可调财务参数 — Edit green cells below · Formulas auto-update on change / 修改绿色单元格，右侧公式自动重算")
    c.font = Font("Calibri", size=9, bold=True, color="FFFFFF")
    c.fill = _fill(C_MID); c.alignment = _align("left")
    ws3.row_dimensions[2].height = 18

    # ── Parameter labels row 3 & values row 4 ────────────────
    # Parameters mapped to columns B-L (2-12)
    # B5: Base PV Save  C5: Base BESS Save  D5: Esc%  E5: Disc%  F5: Tax%
    # G5: PV Deg%  H5: Total CAPEX  I5: PV kWp  J5: BESS kWh
    # K5: PV O&M  L5: BESS O&M
    param_meta = [
        # (col_idx, label, value, editable, fmt)
        (2,  "Yr1 PV Save\nPV节省基期\n(ZAR) 🔒",       d1["annual_pv_saving_ZAR"],   False, "#,##0"),
        (3,  "Yr1 BESS Save\nBESS节省基期\n(ZAR) 🔒",   d1["annual_bess_saving_ZAR"], False, "#,##0"),
        (4,  "Tariff Esc.\n电费增速\n(%/yr) 🟢 Adj.",    ss.tariff_escalation,         True,  "0.0"),
        (5,  "Discount Rate\n折现率\n(%) 🟢 Adj.",       ss.discount_rate,             True,  "0.0"),
        (6,  "Tax Rate\n税率\n(%) 🟢 Adj.",              ss.tax_rate,                  True,  "0.0"),
        (7,  "PV Degrad.\nPV衰减\n(%/yr) 🟢 Adj.",      ss.pv_degradation,            True,  "0.00"),
        (8,  "Total CAPEX\n总投资\n(ZAR) 🔒",            res["total_capex"],           False, "#,##0"),
        (9,  "PV Capacity\n光伏容量\n(kWp) 🔒",         ss.pv_kwp,                    False, "#,##0.0"),
        (10, "BESS Capacity\n储能容量\n(kWh) 🔒",       ss.bess_kwh,                  False, "#,##0.0"),
        (11, "PV O&M\nPV运维\n(ZAR/kWp) 🟢 Adj.",      ss.pv_opex_per_kwp,           True,  "0.00"),
        (12, "BESS O&M\nBESS运维\n(ZAR/kWh) 🟢 Adj.",  ss.bess_opex_per_kwh,         True,  "0.00"),
    ]
    ws3.row_dimensions[3].height = 34
    ws3.row_dimensions[4].height = 20
    ws3.row_dimensions[5].height = 6   # thin divider
    for ci_p, lbl_p, val_p, edit_p, fmt_p in param_meta:
        # Label row 3
        lc3 = ws3.cell(row=3, column=ci_p, value=lbl_p)
        lc3.font = _font(sz=8, bold=True)
        lc3.fill = _fill(C_LTBLUE)
        lc3.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        lc3.border = _bdr()
        # Value row 4
        vc4 = ws3.cell(row=4, column=ci_p, value=val_p)
        vc4.font = _font(sz=10, bold=True,
                         color=C_DARK if not edit_p else "1B5E20")
        # Green bg = editable; yellow bg = locked simulation result
        vc4.fill = _fill("E8F5E9" if edit_p else C_LOCKED)
        vc4.alignment = _align("center")
        vc4.border = _bdr()
        vc4.number_format = fmt_p

    # Label col A rows 3-4
    for r_ in (3, 4):
        ac = ws3.cell(row=r_, column=1,
                      value=("参数名" if r_ == 3 else "参数值"))
        ac.font = _font(sz=8, bold=True, color="FFFFFF")
        ac.fill = _fill(C_NAVY); ac.alignment = _align("center"); ac.border = _bdr()
    # Fill cols M-Q rows 3-4 as spacers
    for r_ in (3, 4):
        for ci_sp in range(13, 18):
            ws3.cell(row=r_, column=ci_sp).fill = _fill(C_ALT)
            ws3.cell(row=r_, column=ci_sp).border = _bdr()

    # Divider row 5
    ws3.merge_cells("A5:Q5")
    ws3.cell(row=5, column=1).fill = _fill(C_NAVY)

    # ── Column headers row 6 ─────────────────────────────────
    hdrs3 = ["年份\nYear", "BESS\n状态", "SOH\n%",
             "PV节省\nZAR", "BESS节省\nZAR", "总节省\nZAR",
             "PV运维\nZAR", "BESS运维\nZAR", "EBITDA\nZAR",
             "12B折旧\nZAR", "税盾\nZAR", "EBIT\nZAR",
             "现金税\nZAR", "净现金流\nNCF ZAR", "折现CF\nPV ZAR",
             "累计CF\nZAR", "净利润\nZAR"]
    for ci, hdr in enumerate(hdrs3, 1):
        hc = ws3.cell(row=6, column=ci, value=hdr)
        hc.font = Font("Calibri", size=8, bold=True, color="FFFFFF")
        hc.fill = _fill(C_NAVY)
        hc.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        hc.border = _bdr()
    ws3.row_dimensions[6].height = 32

    # ── Year 0 row (row 7) ────────────────────────────────────
    # $H$4 = Total CAPEX (parameter value cell)
    r0 = 7
    y0 = ws3.cell(row=r0, column=1, value=0)
    y0.font = _font(bold=True, sz=10); y0.fill = _fill(C_ALT)
    y0.alignment = _align("center"); y0.border = _bdr()
    ws3.merge_cells(start_row=r0, start_column=2, end_row=r0, end_column=13)
    lc = ws3.cell(row=r0, column=2, value="初始投资 / Initial Investment")
    lc.font = Font("Calibri", size=10, bold=True, color=C_RED)
    lc.fill = _fill(C_ALT); lc.alignment = _align("center"); lc.border = _bdr()
    for col_y0, formula_y0 in [
        (14, "=$H$4*-1"),   # NCF yr0 = -CAPEX
        (15, "=$H$4*-1"),   # DiscCF yr0
        (16, "=$H$4*-1"),   # CumCF yr0
    ]:
        cc = ws3.cell(row=r0, column=col_y0, value=formula_y0)
        cc.font = Font("Calibri", size=10, bold=True, color=C_RED)
        cc.fill = _fill("FFF0F0"); cc.alignment = _align("center")
        cc.number_format = "#,##0"; cc.border = _bdr()
    ws3.row_dimensions[r0].height = 20

    # ── Years 1-25 (rows 8-32) ───────────────────────────────
    # Parameter absolute refs:  $B$4=BasePVSave  $C$4=BaseBESSSave
    #   $D$4=Esc%  $E$4=Disc%  $F$4=Tax%  $G$4=PVDeg%
    #   $H$4=CAPEX  $I$4=PVkWp  $J$4=BESSCkWh  $K$4=PVOM  $L$4=BESSOM

    for yr in range(1, 26):
        r = r0 + yr          # rows 8..32
        sv    = soh_arr[yr] if yr < len(soh_arr) else 0.0
        alive = sv >= BESS_EOL_SOH
        alt_bg = C_ALT if yr % 2 == 0 else "FFFFFF"
        dep_pct = SECTION_12B.get(yr, 0.0)

        def _wc(col, val=None, formula=None, fmt="#,##0",
                bg=None, bold=False, color="1A1A2E"):
            cell = ws3.cell(row=r, column=col,
                            value=(formula if formula else val))
            cell.fill = _fill(bg or alt_bg)
            cell.font = Font("Calibri", size=9, bold=bold, color=color)
            cell.alignment = _align("center")
            cell.number_format = fmt
            cell.border = _bdr()
            return cell

        # Col A: Year number
        _wc(1, val=yr, fmt="0", bold=True, bg=C_LTBLUE)

        # Col B: BESS status
        if bess_zero:
            b_label, b_color = "— N/A", "888888"
        elif alive:
            b_label, b_color = "✓ Active", C_GREEN
        else:
            b_label, b_color = "✗ EoL", C_RED
        bs = ws3.cell(row=r, column=2, value=b_label)
        bs.font = Font("Calibri", size=9, bold=True, color=b_color)
        bs.fill = _fill(alt_bg); bs.alignment = _align("center"); bs.border = _bdr()

        # Col C: SOH% (static from computation, not formula)
        soh_pct = round(sv * 100, 2) if not bess_zero else 0.0
        soh_color = (C_GREEN if alive else C_RED) if not bess_zero else "888888"
        _wc(3, val=soh_pct, fmt="0.0", color=soh_color, bold=True)

        # Col D: PV Saving = $B$4 × (1+$D$4/100)^(yr-1) × (1-$G$4/100)^(yr-1)
        _wc(4, formula=f"=$B$4*(1+$D$4/100)^(A{r}-1)*(1-$G$4/100)^(A{r}-1)")

        # Col E: BESS Saving (0 when no BESS installed)
        if bess_zero:
            _wc(5, val=0)
        else:
            # IF(SOH% >= 60, BaseBESS × esc_factor × SOH/100, 0)
            _wc(5, formula=f"=IF(C{r}>=60,$C$4*(1+$D$4/100)^(A{r}-1)*C{r}/100,0)")

        # Col F: Total Saving = D + E
        _wc(6, formula=f"=D{r}+E{r}", bold=True)

        # Col G: PV O&M = PV_kWp × rate × (1 + esc×0.5)^(yr-1)
        _wc(7, formula=f"=$I$4*$K$4*(1+$D$4/200)^(A{r}-1)")

        # Col H: BESS O&M (0 if no BESS or past EoL)
        if bess_zero or not alive:
            _wc(8, val=0, bg=("FFEEEE" if (not bess_zero and not alive) else alt_bg))
        else:
            _wc(8, formula=f"=$J$4*$L$4*(1+$D$4/200)^(A{r}-1)")

        # Col I: EBITDA = F - G - H
        _wc(9, formula=f"=F{r}-G{r}-H{r}", bold=True)

        # Col J: Section 12B Depreciation
        if dep_pct > 0:
            _wc(10, formula=f"=$H$4*{dep_pct}")
        else:
            _wc(10, val=0)

        # Col K: Tax Shield = Dep × Tax%
        if dep_pct > 0:
            _wc(11, formula=f"=J{r}*$F$4/100")
        else:
            _wc(11, val=0)

        # Col L: EBIT = EBITDA - Depreciation
        _wc(12, formula=f"=I{r}-J{r}")

        # Col M: Cash Tax = MAX(0, EBIT × Tax%)
        _wc(13, formula=f"=MAX(0,L{r}*$F$4/100)")

        # Col N: Net Cash Flow = EBITDA - Cash Tax (depreciation is non-cash)
        ncf_val = float(fin_df["净现金流 NCF (ZAR)"].iloc[yr - 1])
        _wc(14, formula=f"=I{r}-M{r}", bold=True,
            color=C_GREEN if ncf_val > 0 else C_RED)

        # Col O: Discounted CF = NCF / (1 + disc%)^yr
        _wc(15, formula=f"=N{r}/(1+$E$4/100)^A{r}")

        # Col P: Cumulative CF
        cum_prev = f"P{r - 1}" if yr > 1 else f"P{r0}"
        _wc(16, formula=f"={cum_prev}+N{r}", bold=True)

        # Col Q: Net Profit = EBIT - Cash Tax
        _wc(17, formula=f"=L{r}-M{r}")
        ws3.row_dimensions[r].height = 16

    # ── Totals row (row 33) ───────────────────────────────────
    r_tot = r0 + 26   # = 33
    ws3.merge_cells(start_row=r_tot, start_column=1, end_row=r_tot, end_column=3)
    tc_lbl = ws3.cell(row=r_tot, column=1, value="25年合计 / 25Y Total")
    tc_lbl.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    tc_lbl.fill = _fill(C_NAVY); tc_lbl.alignment = _align("center"); tc_lbl.border = _bdr()
    for ci_s, cl_s in {4:"D",5:"E",6:"F",7:"G",8:"H",9:"I",
                        10:"J",11:"K",12:"L",13:"M",14:"N",15:"O",17:"Q"}.items():
        ts = ws3.cell(row=r_tot, column=ci_s,
                      value=f"=SUM({cl_s}8:{cl_s}{r_tot-1})")
        ts.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
        ts.fill = _fill(C_NAVY); ts.alignment = _align("center")
        ts.number_format = "#,##0"; ts.border = _bdr()
    tc_cum = ws3.cell(row=r_tot, column=16, value=f"=P{r_tot-1}")
    tc_cum.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    tc_cum.fill = _fill(C_NAVY); tc_cum.alignment = _align("center")
    tc_cum.number_format = "#,##0"; tc_cum.border = _bdr()
    ws3.row_dimensions[r_tot].height = 20

    # ════════════════════════════════════════════════════════════
    # SHEET 4 — 月度汇总 Monthly
    # ════════════════════════════════════════════════════════════
    ws4 = wb.create_sheet("月度汇总 Monthly")
    ws4.sheet_view.showGridLines = False
    for ci, w in enumerate([2, 16, 14, 14, 14, 14, 14, 14, 14], 1):
        ws4.column_dimensions[get_column_letter(ci)].width = w

    ws4.merge_cells("B1:I1")
    c = ws4.cell(row=1, column=2,
                 value="月度调度汇总 / Monthly Dispatch Summary — Year 1")
    c.font = Font("Calibri", size=12, bold=True, color="FFFFFF")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws4.row_dimensions[1].height = 26

    for ci, hdr in enumerate(
        ["月份\nMonth", "PV发电\nkWh", "PV→负载\nkWh", "BESS放电\nkWh",
         "购电量\nGrid kWh", "PV节省\nZAR", "BESS节省\nZAR", "总节省\nZAR"], 2
    ):
        hc = ws4.cell(row=2, column=ci, value=hdr)
        hc.font = Font("Calibri", size=9, bold=True, color="FFFFFF")
        hc.fill = _fill(C_DARK)
        hc.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        hc.border = _bdr()
    ws4.row_dimensions[2].height = 28

    mon_grp = h_df.groupby("month").agg(
        pv_gen=("pv_gen_kWh", "sum"),
        pv_to_load=("pv_to_load_kWh", "sum"),
        discharge=("discharge_kWh", "sum"),
        grid_buy=("grid_buy_kWh", "sum"),
        pv_save=("pv_saving_ZAR", "sum"),
        bess_save=("bess_net_saving_ZAR", "sum"),
        total_save=("net_saving_ZAR", "sum"),
    ).reset_index().sort_values("month")

    mon_names_full = {
        1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
        7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"
    }
    for _, mrow in mon_grp.iterrows():
        mr = int(mrow["month"]) + 2      # rows 3-14
        alt_m = C_ALT if int(mrow["month"]) % 2 == 0 else "FFFFFF"
        mc = ws4.cell(row=mr, column=2, value=mon_names_full.get(int(mrow["month"]), ""))
        mc.font = _font(bold=True, sz=10); mc.fill = _fill(C_LTBLUE)
        mc.alignment = _align(); mc.border = _bdr()
        for ci, key in enumerate(["pv_gen","pv_to_load","discharge","grid_buy",
                                   "pv_save","bess_save","total_save"], 3):
            vc = ws4.cell(row=mr, column=ci, value=round(float(mrow[key]), 0))
            vc.fill = _fill(alt_m); vc.alignment = _align("center")
            vc.number_format = "#,##0"; vc.border = _bdr(); vc.font = _font(sz=10)
        ws4.row_dimensions[mr].height = 17

    # Totals row 15
    mtt = ws4.cell(row=15, column=2, value="全年合计 / Annual Total")
    mtt.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    mtt.fill = _fill(C_NAVY); mtt.alignment = _align("center"); mtt.border = _bdr()
    for ci, cl in enumerate(["C","D","E","F","G","H","I"], 3):
        tc = ws4.cell(row=15, column=ci, value=f"=SUM({cl}3:{cl}14)")
        tc.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
        tc.fill = _fill(C_NAVY); tc.alignment = _align("center")
        tc.number_format = "#,##0"; tc.border = _bdr()
    ws4.row_dimensions[15].height = 20

    # ════════════════════════════════════════════════════════════
    # SHEET 5 — 图表 Charts
    # Sheet3 data: header row 6, Year0 row 7, Years 1-25 rows 8-32, totals row 33
    # Chart data range: rows 6-32 (includes header for title), categories rows 7-32
    # BESS charts skipped when bess_zero=True
    # ════════════════════════════════════════════════════════════
    ws5 = wb.create_sheet("图表 Charts")
    ws5.sheet_view.showGridLines = False
    ws5.column_dimensions["A"].width = 2

    ws5.merge_cells("A1:R1")
    bess_chart_note = "" if not bess_zero else "  (BESS=0 — BESS charts omitted / BESS图表已省略)"
    c = ws5.cell(row=1, column=1,
                 value=f"Charts / 图表 — Linked to Sheet3 & Sheet4 · Auto-updates on parameter change / 参数修改后自动更新{bess_chart_note}")
    c.font = Font("Calibri", size=11, bold=True, color="FFFFFF")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws5.row_dimensions[1].height = 24

    # Shared category reference: col A rows 7-32 (year 0..25)
    _cat = Reference(ws3, min_col=1, max_col=1, min_row=7, max_row=32)
    # Shared category reference for years 1-25 only
    _cat_yr1 = Reference(ws3, min_col=1, max_col=1, min_row=8, max_row=32)

    # Chart 1: Cumulative CF line (col P=16, rows 6-32)
    ch1 = LineChart()
    ch1.title = "25年累计现金流 / Cumulative Cash Flow (ZAR)"
    ch1.style = 10; ch1.width = 17; ch1.height = 11
    ch1.y_axis.title = "ZAR"; ch1.x_axis.title = "Year"
    ch1.add_data(Reference(ws3, min_col=16, max_col=16, min_row=6, max_row=32),
                 titles_from_data=True)
    ch1.set_categories(_cat)
    ws5.add_chart(ch1, "B3")

    # Chart 2: Annual NCF bar (col N=14, rows 6-32)
    ch2 = BarChart()
    ch2.type = "col"
    ch2.title = "年度净现金流 / Annual Net Cash Flow (ZAR)"
    ch2.style = 10; ch2.width = 17; ch2.height = 11
    ch2.y_axis.title = "ZAR"; ch2.x_axis.title = "Year"
    ch2.add_data(Reference(ws3, min_col=14, max_col=14, min_row=6, max_row=32),
                 titles_from_data=True)
    ch2.set_categories(_cat)
    ws5.add_chart(ch2, "L3")

    # Chart 3: BESS SOH degradation — only when BESS installed
    chart3_anchor = "B24"
    if not bess_zero:
        ch3 = LineChart()
        ch3.title = "BESS SOH 衰减 / Battery SOH Degradation (%)"
        ch3.style = 10; ch3.width = 17; ch3.height = 11
        ch3.y_axis.title = "SOH (%)"; ch3.x_axis.title = "Year"
        ch3.add_data(Reference(ws3, min_col=3, max_col=3, min_row=6, max_row=32),
                     titles_from_data=True)
        ch3.set_categories(_cat_yr1)
        ws5.add_chart(ch3, chart3_anchor)

    # Chart 4: Annual savings breakdown
    ch4 = BarChart()
    ch4.type = "col"
    if not bess_zero:
        ch4.grouping = "stacked"
        ch4.title = "PV & BESS 年度节省 / Annual Savings Breakdown (ZAR)"
        # D=PV savings, E=BESS savings — both series
        ch4.add_data(Reference(ws3, min_col=4, max_col=5, min_row=6, max_row=32),
                     titles_from_data=True)
    else:
        ch4.title = "PV 年度节省 / Annual PV Savings (ZAR)"
        # Only D=PV savings when no BESS
        ch4.add_data(Reference(ws3, min_col=4, max_col=4, min_row=6, max_row=32),
                     titles_from_data=True)
    ch4.style = 10; ch4.width = 17; ch4.height = 11
    ch4.y_axis.title = "ZAR"; ch4.x_axis.title = "Year"
    ch4.set_categories(_cat_yr1)
    ws5.add_chart(ch4, "L24")

    # Chart 5: Monthly PV generation bar (ws4 col C=3, rows 2-14)
    ch5 = BarChart()
    ch5.type = "col"
    ch5.title = "月度 PV 发电量 / Monthly PV Generation (kWh)"
    ch5.style = 10; ch5.width = 17; ch5.height = 11
    ch5.y_axis.title = "kWh"; ch5.x_axis.title = "Month"
    ch5.add_data(Reference(ws4, min_col=3, max_col=3, min_row=2, max_row=14),
                 titles_from_data=True)
    ch5.set_categories(Reference(ws4, min_col=2, max_col=2, min_row=3, max_row=14))
    chart5_anchor = "B45" if not bess_zero else "B24"
    ws5.add_chart(ch5, chart5_anchor)

    # ════════════════════════════════════════════════════════════
    # SHEET 6 — 原始数据 Raw Data (8760h)
    # ════════════════════════════════════════════════════════════
    ws6 = wb.create_sheet("原始数据 Raw Data")
    ws6.freeze_panes = "A2"
    h_cols = list(h_df.columns)
    ws6.auto_filter.ref = f"A1:{get_column_letter(len(h_cols))}1"
    for ci, hdr in enumerate(h_cols, 1):
        hc = ws6.cell(row=1, column=ci, value=hdr)
        hc.font = Font("Calibri", size=9, bold=True, color="FFFFFF")
        hc.fill = _fill(C_NAVY); hc.alignment = _align("center"); hc.border = _bdr()
        ws6.column_dimensions[get_column_letter(ci)].width = max(10, len(str(hdr)) + 2)
    ws6.row_dimensions[1].height = 18
    for record in h_df.round(3).itertuples(index=False):
        ws6.append(list(record))

    # ── Serialize ─────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# 页头 / Header
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div style="font-size:1.8rem">⚡</div>
    <div>
        <div class="main-title">专业级 BTM 光储财务测算系统 &nbsp;·&nbsp; Professional BTM PV+BESS Financial Modelling System</div>
        <div class="sub-title">SA MEGAFLEX / MINIFLEX TARIFF 2025/26 &nbsp;·&nbsp; 8760H PHYSICAL DISPATCH ENGINE &nbsp;·&nbsp; SECTION 12B &nbsp;·&nbsp; HUAWEI SA DIGITAL POWER</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 主布局：内容区（左7）+ 参数面板（右3）
# Main layout: content (left 7) + params panel (right 3)
# ─────────────────────────────────────────────────────────────
col_content, col_params = st.columns([7, 3], gap="large")

# ══════════════════════════════════════════════════════════════
# 右侧参数面板 / RIGHT SIDE — Parameter Panel
# ══════════════════════════════════════════════════════════════
with col_params:

    # ── 参数管理 / Parameter Management ──
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 暂存 / Save", use_container_width=True):
            st.session_state.stashed_params = {k: st.session_state[k] for k in DEFAULT_PARAMS}
            st.toast("✓ 已暂存 / Params saved")
    with c2:
        if st.button("📤 恢复 / Restore", use_container_width=True):
            if st.session_state.stashed_params:
                for k, v in st.session_state.stashed_params.items():
                    st.session_state[k] = v
                st.toast("✓ 已恢复 / Params restored")
            else:
                st.toast("⚠️ 无暂存数据 / Nothing saved yet")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # 1. 项目选址 / Site Location
    # ══════════════════════════════════════════════════════════
    with st.expander("📍 项目选址 / Site Location", expanded=True):
        if MAP_AVAILABLE:
            m = folium.Map(
                location=[st.session_state.lat, st.session_state.lon],
                zoom_start=7,
                tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                attr="Google Satellite",
            )
            folium.Marker(
                location=[st.session_state.lat, st.session_state.lon],
                popup=f"📍 {st.session_state.lat:.4f}, {st.session_state.lon:.4f}",
                icon=folium.Icon(color="red", icon="map-pin", prefix="fa"),
            ).add_to(m)
            map_data = st_folium(m, width=None, height=200, key="site_map")

            # 状态隔离防崩溃：临时变量流转地图点击 / Anti-crash via temp vars
            if map_data and map_data.get("last_clicked"):
                _tmp_lat = map_data["last_clicked"]["lat"]
                _tmp_lon = map_data["last_clicked"]["lng"]
                if (abs(_tmp_lat - st.session_state.lat) > 1e-5 or
                        abs(_tmp_lon - st.session_state.lon) > 1e-5):
                    st.session_state.lat = _tmp_lat
                    st.session_state.lon = _tmp_lon
                    st.session_state.tilt = round(abs(_tmp_lat), 1)
                    # 南半球朝北=180°，北半球朝南=0° / SH north-facing=180°, NH south-facing=0°
                    st.session_state.azimuth = 180.0 if _tmp_lat < 0 else 0.0
                    st.rerun()
        else:
            st.info("Install folium + streamlit-folium to enable the map / 安装后重启即可启用地图")

        ca, cb = st.columns(2)
        with ca:
            new_lat = st.number_input("纬度 Lat", value=st.session_state.lat,
                                      min_value=-90.0, max_value=90.0,
                                      format="%.4f", key="_lat_in")
        with cb:
            new_lon = st.number_input("经度 Lon", value=st.session_state.lon,
                                      min_value=-180.0, max_value=180.0,
                                      format="%.4f", key="_lon_in")

        if abs(new_lat - st.session_state.lat) > 1e-5:
            st.session_state.lat = new_lat
            st.session_state.tilt = round(abs(new_lat), 1)
            st.session_state.azimuth = 180.0 if new_lat < 0 else 0.0
        if abs(new_lon - st.session_state.lon) > 1e-5:
            st.session_state.lon = new_lon

        # 自动获取 PVGIS（联动地图/坐标变化）
        check_auto_pvgis()

        # PVGIS 状态显示
        ok = "success-box" if "✓" in st.session_state.pvgis_status else "warning-box"
        st.markdown(f'<div class="{ok}" style="font-size:0.7rem">🌤 {st.session_state.pvgis_status}</div>',
                    unsafe_allow_html=True)
        if st.session_state.annual_pv_kwh:
            eq_h = st.session_state.annual_pv_kwh / max(st.session_state.pv_kwp, 1)
            st.markdown(
                f'<div class="derived-value">☀️ {st.session_state.annual_pv_kwh:,.0f} kWh/yr'
                f' ({eq_h:.0f}h equiv)</div>',
                unsafe_allow_html=True
            )

    # ══════════════════════════════════════════════════════════
    # 2. 光伏系统 / PV System
    # ══════════════════════════════════════════════════════════
    with st.expander("☀️ 光伏系统 / PV System", expanded=False):
        pv_kwp = st.number_input("容量 Capacity (kWp)", value=st.session_state.pv_kwp,
                                  min_value=0.0, step=50.0)
        st.session_state.pv_kwp = pv_kwp
        pv_dis = pv_kwp == 0.0

        pv_loss = st.number_input("损耗 Loss (%)", value=st.session_state.pv_loss,
                                   min_value=0.0, max_value=50.0, step=0.5,
                                   disabled=pv_dis)
        tilt = st.number_input(
            f"倾角 Tilt (°) [最优≈{abs(st.session_state.lat):.0f}°]",
            value=st.session_state.tilt,
            min_value=0.0, max_value=90.0, step=1.0, disabled=pv_dis
        )
        azimuth = st.number_input(
            "方位角 Azimuth (°, 0=朝赤道/equator-facing)",
            value=st.session_state.azimuth,
            min_value=-180.0, max_value=180.0, step=5.0, disabled=pv_dis
        )
        pv_deg = st.number_input("年光衰 Annual Degradation (%)",
                                  value=st.session_state.pv_degradation,
                                  min_value=0.0, max_value=5.0, step=0.1,
                                  disabled=pv_dis)
        if not pv_dis:
            st.session_state.pv_loss       = pv_loss
            st.session_state.tilt          = tilt
            st.session_state.azimuth       = azimuth
            st.session_state.pv_degradation = pv_deg

    # ══════════════════════════════════════════════════════════
    # 3. 储能系统 / BESS System
    # ══════════════════════════════════════════════════════════
    with st.expander("🔋 储能系统 / BESS System", expanded=False):
        bess_kwh = st.number_input("容量 Capacity (kWh)", value=st.session_state.bess_kwh,
                                    min_value=0.0, step=50.0)
        st.session_state.bess_kwh = bess_kwh

        # C倍率选择器（参考值）/ C-rate selector (reference only)
        c_rate_label = st.radio(
            "C倍率 C-rate",
            options=list(C_RATE_OPTIONS.keys()),
            index=list(C_RATE_OPTIONS.keys()).index(st.session_state.c_rate_label),
            horizontal=True,
        )
        st.session_state.c_rate_label = c_rate_label
        c_rate_val = C_RATE_OPTIONS[c_rate_label]
        bess_kw_max = bess_kwh * c_rate_val   # 硬件最大功率 = C率 × 容量
        st.markdown(
            f'<div class="derived-value">⚡ 最大功率 Max Power: <b>{bess_kw_max:.0f} kW</b> '
            f'({c_rate_label}) — dispatch engine auto-optimises output</div>',
            unsafe_allow_html=True
        )

        rte = st.number_input("充放效率 RTE (%)", value=st.session_state.rte,
                               min_value=50.0, max_value=100.0, step=0.5)
        dod = st.number_input("放电深度 DoD (%)", value=st.session_state.dod,
                               min_value=50.0, max_value=100.0, step=1.0)  # max=100% allowed
        bess_cycles = st.number_input("标称循环 Cycles", value=int(st.session_state.bess_cycles),
                                       min_value=1000, max_value=20000, step=500)

        st.session_state.rte         = rte
        st.session_state.dod         = dod
        st.session_state.bess_cycles = bess_cycles

    # ══════════════════════════════════════════════════════════
    # 4. 厂区负载 / Site Load Profile
    # ══════════════════════════════════════════════════════════
    with st.expander("🏭 厂区负载 / Load Profile", expanded=False):
        st.markdown('<div class="param-label">高峰时段负载 Peak hours (07-10, 18-20h)</div>',
                    unsafe_allow_html=True)
        load_peak = st.number_input("高峰 Peak Load (kW)", value=st.session_state.load_peak_kw,
                                     min_value=0.0, step=10.0,
                                     label_visibility="collapsed")
        st.markdown('<div class="param-label">平期负载 Standard hours (06-07, 10-18, 20-22h)</div>',
                    unsafe_allow_html=True)
        load_std = st.number_input("平期 Standard Load (kW)", value=st.session_state.load_std_kw,
                                    min_value=0.0, step=10.0,
                                    label_visibility="collapsed")
        st.markdown('<div class="param-label">谷期负载 Off-peak hours (22-06h)</div>',
                    unsafe_allow_html=True)
        load_offpeak = st.number_input("谷期 Off-Peak Load (kW)", value=st.session_state.load_offpeak_kw,
                                        min_value=0.0, step=5.0,
                                        label_visibility="collapsed")

        st.session_state.load_peak_kw    = load_peak
        st.session_state.load_std_kw     = load_std
        st.session_state.load_offpeak_kw = load_offpeak

        # 估算日用电量 / Estimated daily energy
        # 高峰: 5h(07-10 3h + 18-20 2h), 谷: 8h(22-06), 平: 11h
        est_daily = load_peak * 5 + load_std * 11 + load_offpeak * 8
        st.markdown(
            f'<div class="derived-value">📊 Est. daily load ≈ {est_daily:.0f} kWh/day'
            f' ({est_daily*365/1000:.0f} MWh/yr)</div>',
            unsafe_allow_html=True
        )

    # ══════════════════════════════════════════════════════════
    # 5. Eskom 电价（2025/26）/ Eskom Tariffs
    # ══════════════════════════════════════════════════════════
    with st.expander("💡 Eskom 电价 / Tariffs (ZAR/kWh)", expanded=False):

        # 电价模式选择器 / Tariff mode selector (auto-populates rates from TARIFF_DB)
        all_modes = list(TARIFF_DB.keys())
        cur_mode  = st.session_state.get("tariff_mode", "Megaflex ≤300km <500V")
        if cur_mode not in all_modes:
            cur_mode = all_modes[0]
        tariff_mode = st.selectbox(
            "电价模式 Tariff Mode",
            all_modes,
            index=all_modes.index(cur_mode),
            key="tariff_mode_sel",
        )

        # Auto-populate rates when mode changes; do NOT overwrite on same mode
        prev_mode = st.session_state.get("_prev_tariff_mode")
        if tariff_mode != prev_mode:
            st.session_state.tariff_mode = tariff_mode
            if tariff_mode != "Custom (manual)" and TARIFF_DB.get(tariff_mode):
                w_pk, w_std, w_op, s_pk, s_std, s_op = TARIFF_DB[tariff_mode]
                st.session_state.w_morning_peak = w_pk
                st.session_state.w_evening_peak = w_pk
                st.session_state.w_standard     = w_std
                st.session_state.w_off_peak     = w_op
                st.session_state.s_morning_peak = s_pk
                st.session_state.s_evening_peak = s_pk
                st.session_state.s_standard     = s_std
                st.session_state.s_off_peak     = s_op
            st.session_state._prev_tariff_mode = tariff_mode
            st.rerun()

        if tariff_mode == "PPA 自定义 (flat rate)":
            st.caption("PPA 模式：输入单一购电单价，所有时段同价 / PPA: enter one flat rate applied to all periods")
            ppa_rate = st.number_input(
                "PPA 电价 PPA Rate (ZAR/kWh)",
                value=st.session_state.get("ppa_rate", 1.20),
                min_value=0.10, max_value=5.00, step=0.05, format="%.2f",
            )
            st.session_state.ppa_rate = ppa_rate
            # 将所有时段统一设为 PPA 单价
            for key in ("w_morning_peak","w_evening_peak","w_standard","w_off_peak",
                        "s_morning_peak","s_evening_peak","s_standard","s_off_peak"):
                st.session_state[key] = ppa_rate
        elif tariff_mode == "Custom (manual)":
            st.caption("自定义模式：手动输入所有电价 / Custom: edit all rates below")
        else:
            st.caption("选择电价模式后自动填充；也可手动微调 / Select mode to auto-fill; manual edits override")

        st.markdown('<div class="tariff-winter"><b style="color:#4ECDC4">❄️ 高峰季 High Season (Jun-Aug)</b></div>',
                    unsafe_allow_html=True)
        cw1, cw2 = st.columns(2)
        with cw1:
            st.session_state.w_morning_peak = st.number_input(
                "早峰 Morn Peak", value=st.session_state.w_morning_peak,
                min_value=0.1, step=0.05, format="%.2f")
            st.session_state.w_standard = st.number_input(
                "平期 Standard", value=st.session_state.w_standard,
                min_value=0.1, step=0.05, format="%.2f")
        with cw2:
            st.session_state.w_evening_peak = st.number_input(
                "晚峰 Eve Peak", value=st.session_state.w_evening_peak,
                min_value=0.1, step=0.05, format="%.2f")
            st.session_state.w_off_peak = st.number_input(
                "谷期 Off-Peak", value=st.session_state.w_off_peak,
                min_value=0.05, step=0.05, format="%.2f")

        st.markdown('<div class="tariff-summer"><b style="color:#F6C90E">☀️ 低谷季 Low Season (Sep-May)</b></div>',
                    unsafe_allow_html=True)
        cs1, cs2 = st.columns(2)
        with cs1:
            st.session_state.s_morning_peak = st.number_input(
                "早峰 Morn Peak ", value=st.session_state.s_morning_peak,
                min_value=0.1, step=0.05, format="%.2f")
            st.session_state.s_standard = st.number_input(
                "平期 Standard ", value=st.session_state.s_standard,
                min_value=0.1, step=0.05, format="%.2f")
        with cs2:
            st.session_state.s_evening_peak = st.number_input(
                "晚峰 Eve Peak ", value=st.session_state.s_evening_peak,
                min_value=0.1, step=0.05, format="%.2f")
            st.session_state.s_off_peak = st.number_input(
                "谷期 Off-Peak ", value=st.session_state.s_off_peak,
                min_value=0.05, step=0.05, format="%.2f")

        # 峰谷价差显示 / Peak-valley spread display
        w_spread = st.session_state.w_morning_peak - st.session_state.w_off_peak
        s_spread = st.session_state.s_morning_peak - st.session_state.s_off_peak
        st.markdown(
            f'<div class="derived-value">'
            f'❄️峰谷差 {w_spread:.2f} | ☀️峰谷差 {s_spread:.2f} ZAR/kWh'
            f'</div>',
            unsafe_allow_html=True
        )

    # ══════════════════════════════════════════════════════════
    # 6. 财务参数 / Financial Parameters
    # ══════════════════════════════════════════════════════════
    with st.expander("💰 财务参数 / Financials", expanded=False):

        # 汇率 / Forex
        fx_col1, fx_col2 = st.columns([3, 1])
        with fx_col1:
            forex = st.number_input("USD/ZAR 汇率", value=st.session_state.forex_usd_zar,
                                     min_value=1.0, step=0.1, format="%.2f")
            st.session_state.forex_usd_zar = forex
        with fx_col2:
            if st.button("🔄", help="实时刷新汇率 / Refresh live rate",
                          use_container_width=True):
                live = fetch_forex_rate()
                st.session_state.forex_usd_zar = live
                st.toast(f"汇率更新: 1 USD = {live:.2f} ZAR")
                st.rerun()

        # PV & BESS 美元造价 / USD unit costs
        pv_usd = st.number_input("PV造价 (USD/W)", value=st.session_state.pv_usd_per_w,
                                  min_value=0.1, step=0.05, format="%.3f",
                                  disabled=pv_kwp == 0)
        bess_usd = st.number_input("BESS造价 (USD/Wh)", value=st.session_state.bess_usd_per_wh,
                                    min_value=0.05, step=0.01, format="%.3f")
        st.session_state.pv_usd_per_w    = pv_usd
        st.session_state.bess_usd_per_wh = bess_usd

        # 换算显示 / Show ZAR equivalents
        pv_zar_kwp, bess_zar_kwh = get_capex_zar()
        st.markdown(
            f'<div class="derived-value">'
            f'PV: {pv_zar_kwp:,.0f} ZAR/kWp | BESS: {bess_zar_kwh:,.0f} ZAR/kWh'
            f'</div>',
            unsafe_allow_html=True
        )

        # O&M
        pv_opex = st.number_input("PV O&M (ZAR/kWp/yr)", value=st.session_state.pv_opex_per_kwp,
                                   min_value=0.0, step=5.0, disabled=pv_kwp == 0)
        bess_opex = st.number_input("BESS O&M (ZAR/kWh/yr)", value=st.session_state.bess_opex_per_kwh,
                                     min_value=0.0, step=1.0)
        st.session_state.pv_opex_per_kwp   = pv_opex
        st.session_state.bess_opex_per_kwh = bess_opex

        # 财务假设 / Financial assumptions
        st.session_state.tariff_escalation = st.number_input(
            "电价涨幅 Tariff Esc. (%/yr)", value=st.session_state.tariff_escalation,
            min_value=0.0, max_value=30.0, step=0.5)
        st.session_state.discount_rate = st.number_input(
            "折现率 Discount Rate (%)", value=st.session_state.discount_rate,
            min_value=0.0, max_value=50.0, step=0.5)
        st.session_state.tax_rate = st.number_input(
            "企业税率 Corp Tax (%)", value=st.session_state.tax_rate,
            min_value=0.0, max_value=50.0, step=1.0)


# ══════════════════════════════════════════════════════════════
# 左侧内容区 / LEFT — Content Area (Tabs)
# ══════════════════════════════════════════════════════════════
with col_content:

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 计算与结果 / Run & Results",
        "📋 25年财务报表 / 25Y Model",
        "⏱️ 8760小时调度 / Hourly Dispatch",
        "🔍 AI 寻优 / Optimization",
    ])

    # ──────────────────────────────────────────────────────────
    # Tab 1: 计算与结果
    # ──────────────────────────────────────────────────────────
    with tab1:
        st.markdown("### 🚀 运行 8760 小时物理仿真 / Run Physical Simulation")

        run_calc = st.button("▶ 开始计算 / Run Simulation", type="primary",
                              use_container_width=True)

        if run_calc:
            if st.session_state.pv_kwp == 0 and st.session_state.bess_kwh == 0:
                st.error("❌ PV and BESS are both 0 — please configure at least one / PV 和 BESS 均为零，请至少配置一项")
            else:
                # 获取或复用 PVGIS 数据
                if "pvgis_data" not in st.session_state or st.session_state.pv_kwp == 0:
                    pvgis_data = get_pvgis_data(
                        st.session_state.lat, st.session_state.lon,
                        max(st.session_state.pv_kwp, 1),
                        st.session_state.pv_loss, st.session_state.tilt, st.session_state.azimuth,
                    )
                    if st.session_state.pv_kwp == 0:
                        pvgis_data.update({"annual_kwh": 0, "monthly_kwh": [0] * 12,
                                           "winter_daily_kwh": 0, "summer_daily_kwh": 0})
                else:
                    pvgis_data = st.session_state.pvgis_data

                # 最大功率由 C倍率 × 容量决定，调度引擎按需自动输出（不人工限制）
                bess_kw_use = st.session_state.bess_kwh * C_RATE_OPTIONS[st.session_state.c_rate_label]

                with st.spinner("⚙️ 正在运行 8760h 物理调度引擎... / Running dispatch engine..."):
                    dispatch_yr1 = run_8760_dispatch(
                        pv_kwp=st.session_state.pv_kwp,
                        bess_kwh=st.session_state.bess_kwh,
                        bess_kw=bess_kw_use,
                        load_peak_kw=st.session_state.load_peak_kw,
                        load_std_kw=st.session_state.load_std_kw,
                        load_offpeak_kw=st.session_state.load_offpeak_kw,
                        rte=st.session_state.rte,
                        dod=st.session_state.dod,
                        pvgis_data=pvgis_data,
                    )

                eol_years, annual_cycles = compute_bess_eol(
                    dispatch_yr1["tot_throughput_kWh"],
                    st.session_state.bess_kwh,
                    int(st.session_state.bess_cycles),
                    st.session_state.dod,
                )

                pv_zar_kwp, bess_zar_kwh = get_capex_zar()
                params = {
                    "pv_capex_per_kwp":   pv_zar_kwp,
                    "bess_capex_per_kwh": bess_zar_kwh,
                    "pv_opex_per_kwp":    st.session_state.pv_opex_per_kwp,
                    "bess_opex_per_kwh":  st.session_state.bess_opex_per_kwh,
                    "tariff_escalation":  st.session_state.tariff_escalation,
                    "discount_rate":      st.session_state.discount_rate,
                    "tax_rate":           st.session_state.tax_rate,
                    "pv_degradation":     st.session_state.pv_degradation,
                }

                with st.spinner("📊 计算 25 年财务模型..."):
                    fin_df = run_25yr_financial_model(
                        dispatch_yr1=dispatch_yr1,
                        pv_kwp=st.session_state.pv_kwp,
                        bess_kwh=st.session_state.bess_kwh,
                        eol_years=eol_years,
                        params=params,
                        annual_cycles=annual_cycles,
                    )

                total_capex = (st.session_state.pv_kwp * pv_zar_kwp +
                               st.session_state.bess_kwh * bess_zar_kwh)
                npv, irr = compute_npv_irr(fin_df, total_capex, params["discount_rate"])

                cum = fin_df["累计CF (ZAR)"].tolist()
                # 线性插值：精确计算回收期（小数年）
                # Linear interpolation for fractional payback year
                payback = None
                for _i, _v in enumerate(cum):
                    if _v >= 0:
                        if _i == 0:
                            payback = float(fin_df["年份 Year"].iloc[0])
                        else:
                            _v0 = cum[_i - 1]          # negative
                            _y0 = float(fin_df["年份 Year"].iloc[_i - 1])
                            payback = _y0 + (-_v0) / (_v - _v0)   # interpolate
                        break

                st.session_state.results = {
                    "dispatch_yr1": dispatch_yr1, "eol_years": eol_years,
                    "annual_cycles": annual_cycles, "pvgis_data": pvgis_data,
                    "npv": npv, "irr": irr, "payback": payback,
                    "total_capex": total_capex, "bess_kw": bess_kw_use,
                }
                st.session_state.hourly_df = dispatch_yr1["hourly_df"]
                st.session_state.fin_df = fin_df
                st.success("✅ 计算完成 / Calculation Complete!")

        # ── 显示结果 / Display results ──
        if st.session_state.results:
            res = st.session_state.results

            st.markdown('<div class="section-header">📈 关键财务指标 / Key Metrics</div>',
                        unsafe_allow_html=True)
            m1, m2, m3, m4, m5 = st.columns(5)

            with m1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">总投资 CAPEX</div>
                    <div class="metric-value">R{res['total_capex']/1e6:.2f}M</div>
                    <div class="metric-unit">ZAR ({st.session_state.forex_usd_zar:.1f} USD/ZAR)</div>
                </div>""", unsafe_allow_html=True)

            with m2:
                c = "var(--primary)" if res['npv'] > 0 else "var(--danger)"
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">净现值 NPV (25yr)</div>
                    <div class="metric-value" style="color:{c}">R{res['npv']/1e6:.2f}M</div>
                    <div class="metric-unit">@ {st.session_state.discount_rate:.1f}% disc</div>
                </div>""", unsafe_allow_html=True)

            with m3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">内部收益率 IRR</div>
                    <div class="metric-value">{res['irr']:.1f}%</div>
                    <div class="metric-unit">25-Year Project IRR</div>
                </div>""", unsafe_allow_html=True)

            with m4:
                pb = f"{res['payback']:.2f}yr" if res['payback'] else "25yr+"
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">回收期 Payback</div>
                    <div class="metric-value">{pb}</div>
                    <div class="metric-unit">Simple Payback</div>
                </div>""", unsafe_allow_html=True)

            with m5:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">BESS EoL</div>
                    <div class="metric-value" style="color:var(--secondary)">Yr {int(res['eol_years'])}</div>
                    <div class="metric-unit">{res['annual_cycles']:.1f} cycles/yr</div>
                </div>""", unsafe_allow_html=True)

            # 运营指标
            st.markdown('<div class="section-header">⚡ 年度运营指标 / Year 1 Operations</div>',
                        unsafe_allow_html=True)
            d = res['dispatch_yr1']
            o1, o2, o3, o4 = st.columns(4)

            with o1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">年总节省 Yr1 Saving</div>
                    <div class="metric-value">R{d['annual_saving_ZAR']/1000:.1f}K</div>
                    <div class="metric-unit">PV:{d['annual_pv_saving_ZAR']/1000:.1f}K + BESS:{d['annual_bess_saving_ZAR']/1000:.1f}K</div>
                </div>""", unsafe_allow_html=True)

            with o2:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">光伏发电 PV Gen</div>
                    <div class="metric-value">{d['annual_pv_gen_kWh']/1000:.1f}</div>
                    <div class="metric-unit">MWh/yr</div>
                </div>""", unsafe_allow_html=True)

            with o3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">总吞吐 Throughput</div>
                    <div class="metric-value">{d['tot_throughput_kWh']/1000:.1f}</div>
                    <div class="metric-unit">MWh (charge×RTE + discharge)</div>
                </div>""", unsafe_allow_html=True)

            with o4:
                self_pct = min(d['annual_pv_gen_kWh'] / max(d['annual_load_kWh'], 1) * 100, 100)
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">PV 自消纳率 / Self-Use</div>
                    <div class="metric-value">{self_pct:.1f}%</div>
                    <div class="metric-unit">PV vs Annual Load</div>
                </div>""", unsafe_allow_html=True)

            # 现金流图表
            st.markdown('<div class="section-header">📊 25年现金流图表 / 25Y Cash Flow</div>',
                        unsafe_allow_html=True)

            if st.session_state.fin_df is not None:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots

                df = st.session_state.fin_df
                eol_yr = int(res['eol_years'])

                fig = make_subplots(rows=1, cols=2,
                                    subplot_titles=("年净现金流 Annual NCF (ZAR)",
                                                    "累计现金流 Cumulative CF (ZAR)"))

                colors = ["#00E5A0" if v >= 0 else "#FF4444" for v in df["净现金流 NCF (ZAR)"]]
                fig.add_trace(go.Bar(x=df["年份 Year"], y=df["净现金流 NCF (ZAR)"],
                                     marker_color=colors, name="NCF",
                                     text=[f"R{v/1000:.0f}K" for v in df["净现金流 NCF (ZAR)"]],
                                     textposition="outside", textfont=dict(size=7)),
                              row=1, col=1)

                fig.add_vline(x=eol_yr, line_dash="dash", line_color="#FF6B35", line_width=2,
                              annotation_text=f"BESS EoL Yr{eol_yr}",
                              annotation_font_color="#FF6B35", row=1, col=1)

                fig.add_trace(go.Scatter(x=df["年份 Year"], y=df["累计CF (ZAR)"],
                                         mode="lines+markers",
                                         line=dict(color="#4ECDC4", width=2),
                                         marker=dict(size=4), fill="tozeroy",
                                         fillcolor="rgba(78,205,196,0.08)",
                                         name="累计CF"),
                              row=1, col=2)

                fig.add_hline(y=0, line_dash="dot", line_color="white", line_width=1, row=1, col=2)
                fig.add_vline(x=eol_yr, line_dash="dash", line_color="#FF6B35", line_width=2,
                              annotation_text="BESS EoL", annotation_font_color="#FF6B35",
                              row=1, col=2)

                fig.update_layout(paper_bgcolor="#0A0E1A", plot_bgcolor="#111827",
                                  font=dict(color="#E8ECF0", family="IBM Plex Mono"),
                                  showlegend=False, height=380,
                                  margin=dict(l=10, r=10, t=50, b=10))
                fig.update_xaxes(gridcolor="#2D3748", title_text="Year")
                fig.update_yaxes(gridcolor="#2D3748")
                st.plotly_chart(fig, use_container_width=True)

            # 导出
            st.markdown('<div class="section-header">📥 数据导出 / Export</div>', unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)

            with dl1:
                if st.session_state.hourly_df is not None:
                    buf = io.StringIO()
                    st.session_state.hourly_df.to_csv(buf, index=False, encoding="utf-8-sig")
                    st.download_button("⬇ 8760_Hourly_Dispatch.csv",
                                       data=buf.getvalue().encode("utf-8-sig"),
                                       file_name="8760_Hourly_Dispatch.csv",
                                       mime="text/csv", use_container_width=True)

            with dl2:
                if st.session_state.fin_df is not None:
                    xbuf = io.BytesIO()
                    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                        st.session_state.fin_df.to_excel(
                            writer, sheet_name="25yr_Financial_Model", index=False)
                        ops = pd.DataFrame([
                            {"指标": "Annual Saving (ZAR)", "值": res['dispatch_yr1']['annual_saving_ZAR']},
                            {"指标": "PV Saving (ZAR)", "值": res['dispatch_yr1']['annual_pv_saving_ZAR']},
                            {"指标": "BESS Net Saving (ZAR)", "值": res['dispatch_yr1']['annual_bess_saving_ZAR']},
                            {"指标": "Annual PV Gen (kWh)", "值": res['dispatch_yr1']['annual_pv_gen_kWh']},
                            {"指标": "Throughput (kWh)", "值": res['dispatch_yr1']['tot_throughput_kWh']},
                            {"指标": "Annual Cycles", "值": res['annual_cycles']},
                            {"指标": "BESS EoL (yr)", "值": res['eol_years']},
                            {"指标": "NPV (ZAR)", "值": res['npv']},
                            {"指标": "IRR (%)", "值": res['irr']},
                            {"指标": "USD/ZAR Rate", "值": st.session_state.forex_usd_zar},
                        ])
                        ops.to_excel(writer, sheet_name="Summary", index=False)
                    st.download_button("⬇ BTM_Pure_Data_Export.xlsx",
                                       data=xbuf.getvalue(),
                                       file_name="BTM_Pure_Data_Export.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       use_container_width=True)

            # ── 专业 Excel 报告（密码保护）/ Professional Excel Report ──
            st.markdown("---")
            st.markdown(
                '<div class="section-header">📊 专业 Excel 报告 / Professional Excel Report</div>',
                unsafe_allow_html=True,
            )
            st.markdown("""<div class="info-box">
                6-sheet 完整报告：封面 · 参数（含 Excel 公式）· 25年财务模型 · 月度汇总 · 图表 · 8760h 原始数据
                &nbsp;|&nbsp; 参数页白色单元格可调，Sheet3 财务模型自动重算 &nbsp;|&nbsp; 需密码授权
            </div>""", unsafe_allow_html=True)

            xpwd_col, xbtn_col, xdl_col = st.columns([2, 1.5, 2])
            with xpwd_col:
                entered_pwd = st.text_input(
                    "🔑 报告密码 Report Password",
                    type="password",
                    key="excel_export_pwd",
                    placeholder="输入密码 Enter password...",
                )
            with xbtn_col:
                st.markdown("<br>", unsafe_allow_html=True)
                gen_excel_btn = st.button(
                    "📊 生成报告 Generate",
                    key="gen_excel_report_btn",
                    use_container_width=True,
                )

            if gen_excel_btn:
                if entered_pwd == "9999":
                    with st.spinner("📊 正在生成 6-sheet 专业 Excel 报告，请稍候..."):
                        try:
                            _xlsx_bytes = generate_excel_report()
                            st.session_state["_excel_rpt_bytes"] = _xlsx_bytes
                            import datetime as _edt
                            _loc = (f"{st.session_state.lat:.1f}_{st.session_state.lon:.1f}"
                                    .replace("-", "S").replace(".", "p"))
                            st.session_state["_excel_rpt_fname"] = (
                                f"BTM_Report_{_loc}_{_edt.datetime.now():%Y%m%d}.xlsx"
                            )
                            st.success("✅ 报告已生成，点击下方按钮下载 / Report ready — click to download")
                        except Exception as _e:
                            st.error(f"❌ 生成失败 Generation failed: {_e}")
                elif entered_pwd:
                    st.error("❌ 密码错误 Wrong password")

            if "_excel_rpt_bytes" in st.session_state:
                with xdl_col:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.download_button(
                        "⬇ 下载专业报告 / Download Excel Report",
                        data=st.session_state["_excel_rpt_bytes"],
                        file_name=st.session_state.get(
                            "_excel_rpt_fname", "BTM_Report.xlsx"),
                        mime=("application/vnd.openxmlformats-"
                              "officedocument.spreadsheetml.sheet"),
                        use_container_width=True,
                    )

    # ──────────────────────────────────────────────────────────
    # Tab 2: 25年财务报表
    # ──────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### 📋 25年逐年财务报表 / 25-Year Annual Financial Statement")

        if st.session_state.fin_df is not None:
            st.markdown("""<div class="info-box">
                📌 <b>Section 12B</b> accelerated depreciation: Yr1 50% · Yr2 25% · Yr3 25% (SA Income Tax Act) &nbsp;|&nbsp;
                PV &amp; BESS savings shown separately &nbsp;|&nbsp; BESS revenue &amp; OPEX zeroed after EoL (SOH &lt; 60%)
            </div>""", unsafe_allow_html=True)

            eol_yr = int(st.session_state.results["eol_years"]) if st.session_state.results else 999

            def highlight_eol(row):
                if row["年份 Year"] > eol_yr:
                    return ["background-color: rgba(255,107,53,0.08)"] * len(row)
                elif row["年份 Year"] <= 3:
                    return ["background-color: rgba(0,229,160,0.05)"] * len(row)
                return [""] * len(row)

            num_cols = {c: "{:,.0f}" for c in st.session_state.fin_df.columns
                        if st.session_state.fin_df[c].dtype in [np.float64, np.int64]
                        and c not in ["年份 Year", "SOH%"]}

            styled = st.session_state.fin_df.style.apply(highlight_eol, axis=1).format(num_cols)
            st.dataframe(styled, use_container_width=True, height=580)

        else:
            st.markdown('<div class="warning-box">⚠️ Please run the simulation first in "Run &amp; Results" tab / 请先在"计算与结果"中运行计算</div>',
                        unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # Tab 3: 8760小时调度
    # ──────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### ⏱️ 8760小时调度明细 / Hourly Dispatch Log")

        if st.session_state.hourly_df is not None:
            import plotly.graph_objects as go

            df_h = st.session_state.hourly_df

            # 月度汇总
            st.markdown('<div class="section-header">📅 月度汇总 / Monthly Summary</div>',
                        unsafe_allow_html=True)
            mth_agg = df_h.groupby("month").agg({
                "pv_gen_kWh": "sum", "charge_grid_kWh": "sum",
                "discharge_kWh": "sum", "grid_buy_kWh": "sum",
                "net_saving_ZAR": "sum",
            }).reset_index()

            mnames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=mnames, y=mth_agg["pv_gen_kWh"],
                                    name="PV Gen", marker_color="#F6C90E"))
            fig_m.add_trace(go.Bar(x=mnames, y=mth_agg["discharge_kWh"],
                                    name="BESS Discharge", marker_color="#00E5A0"))
            fig_m.add_trace(go.Bar(x=mnames, y=mth_agg["charge_grid_kWh"],
                                    name="Grid Charge", marker_color="#4ECDC4"))
            fig_m.add_trace(go.Scatter(x=mnames, y=mth_agg["net_saving_ZAR"],
                                        name="Net Saving (ZAR)", yaxis="y2",
                                        line=dict(color="#FF6B35", width=2),
                                        marker=dict(size=5)))
            # 标注冬季高峰月份 / Mark winter months
            for mi, mn in enumerate(mnames):
                if (mi + 1) in WINTER_MONTHS:
                    fig_m.add_vrect(x0=mn, x1=mn, fillcolor="#4ECDC4",
                                    opacity=0.08, line_width=0)

            fig_m.update_layout(
                barmode="stack", paper_bgcolor="#0A0E1A", plot_bgcolor="#111827",
                font=dict(color="#E8ECF0", family="IBM Plex Mono"),
                yaxis=dict(title="Energy (kWh)", gridcolor="#2D3748"),
                yaxis2=dict(title="Saving (ZAR)", overlaying="y", side="right"),
                legend=dict(bgcolor="#111827", bordercolor="#2D3748", orientation="h"),
                height=320, margin=dict(l=10, r=10, t=20, b=10),
                annotations=[dict(text="❄️高峰季 Jun-Aug", x="Jun", y=1.05,
                                  xref="x", yref="paper", showarrow=False,
                                  font=dict(color="#4ECDC4", size=9))]
            )
            st.plotly_chart(fig_m, use_container_width=True)

            # 典型日剖面
            st.markdown('<div class="section-header">📈 典型日调度剖面 / Typical Day Profile</div>',
                        unsafe_allow_html=True)
            sel_month = st.selectbox("选择月份 / Select Month", range(1, 13),
                                      format_func=lambda x: mnames[x-1], index=6)

            mdata = df_h[df_h["month"] == sel_month]
            if len(mdata) > 0:
                tgt = int(mdata["day"].median())
                ddata = mdata[mdata["day"] == tgt]
                if len(ddata) == 24:
                    fig_d = go.Figure()
                    fig_d.add_trace(go.Scatter(x=ddata["hour_of_day"], y=ddata["load_kWh"],
                                               name="Load", line=dict(color="white", width=2, dash="dot")))
                    fig_d.add_trace(go.Bar(x=ddata["hour_of_day"], y=ddata["pv_gen_kWh"],
                                           name="PV Gen", marker_color="#F6C90E", opacity=0.8))
                    fig_d.add_trace(go.Bar(x=ddata["hour_of_day"], y=ddata["discharge_kWh"],
                                           name="BESS Discharge", marker_color="#00E5A0", opacity=0.8))
                    fig_d.add_trace(go.Bar(x=ddata["hour_of_day"],
                                           y=[-v for v in ddata["charge_grid_kWh"]],
                                           name="Grid Charge", marker_color="#4ECDC4", opacity=0.7))
                    fig_d.add_trace(go.Scatter(x=ddata["hour_of_day"], y=ddata["soc_kWh"],
                                               name="SOC (kWh)", yaxis="y2",
                                               line=dict(color="#FF6B35", width=2)))
                    fig_d.add_trace(go.Scatter(x=ddata["hour_of_day"],
                                               y=ddata["tariff_ZAR_kWh"] * 50,
                                               name="Tariff×50", yaxis="y2",
                                               line=dict(color="#E040FB", width=1.5, dash="dash")))
                    fig_d.update_layout(
                        paper_bgcolor="#0A0E1A", plot_bgcolor="#111827",
                        font=dict(color="#E8ECF0", family="IBM Plex Mono"),
                        barmode="overlay",
                        yaxis=dict(title="kWh/h", gridcolor="#2D3748"),
                        yaxis2=dict(title="SOC/Tariff", overlaying="y", side="right"),
                        legend=dict(bgcolor="#111827", orientation="h"),
                        height=360, margin=dict(l=10, r=10, t=20, b=10),
                        xaxis=dict(title="Hour", tickvals=list(range(24)), gridcolor="#2D3748"),
                    )
                    st.plotly_chart(fig_d, use_container_width=True)

            st.markdown('<div class="section-header">📋 小时明细 / Hourly Log (First 100)</div>',
                        unsafe_allow_html=True)
            st.dataframe(df_h.head(100), use_container_width=True, height=380)

        else:
            st.markdown('<div class="warning-box">⚠️ Run simulation first / 请先运行计算</div>', unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # Tab 4: AI 寻优
    # ──────────────────────────────────────────────────────────
    with tab4:
        st.markdown("### 🔍 max(NPV) 全局容量寻优 / Global Capacity Optimization")

        st.markdown("""<div class="info-box">
            🤖 Sweeps all PV × BESS combinations within 60%–150% of current sizing to find the NPV-maximising configuration.
            BESS step fixed at 5 MWh; PV step is user-adjustable. &nbsp;|&nbsp;
            遍历当前配置 60%~150% 范围内的所有 PV × BESS 组合，寻找最优 NPV。BESS 步长固定 5 MWh，PV 步长可调。
        </div>""", unsafe_allow_html=True)

        # ── 自动计算寻优范围（当前设定值的 60%~150%）──────────────────────────
        _BESS_STEP = 5000.0   # 5 MWh 固定步长
        cur_pv   = float(st.session_state.pv_kwp)
        cur_bess = float(st.session_state.bess_kwh)

        def _snap_bess(v: float) -> float:
            """向最近的 5 MWh 倍数取整"""
            return max(_BESS_STEP, round(v / _BESS_STEP) * _BESS_STEP)

        auto_pv_min   = float(max(100.0, round(cur_pv  * 0.6 / 100) * 100))
        auto_pv_max   = float(max(100.0, round(cur_pv  * 1.5 / 100) * 100))
        auto_bess_min = float(_snap_bess(cur_bess * 0.6))
        auto_bess_max = float(_snap_bess(cur_bess * 1.5))

        oc1, oc2 = st.columns(2)
        with oc1:
            st.markdown(f"**PV Range / PV 范围** (current {cur_pv:.0f} kWp × 60–150%)")
            pv_min = st.number_input("PV Min (kWp)", value=auto_pv_min, min_value=100.0, step=100.0)
            pv_max = st.number_input("PV Max (kWp)", value=auto_pv_max, min_value=100.0, step=100.0)
            pv_stp = st.number_input("PV Step (kWp)", value=200.0, min_value=100.0, step=100.0)
        with oc2:
            st.markdown(f"**BESS Range / BESS 范围** (current {cur_bess/1000:.0f} MWh × 60–150%, fixed 5 MWh step)")
            bess_min = st.number_input("BESS Min (kWh)", value=auto_bess_min,
                                        min_value=_BESS_STEP, step=_BESS_STEP)
            bess_max = st.number_input("BESS Max (kWh)", value=auto_bess_max,
                                        min_value=_BESS_STEP, step=_BESS_STEP)
            # BESS step 固定 5 MWh，不可修改
            st.markdown(f'<div class="derived-value">BESS Step fixed at 5 MWh (5,000 kWh) / BESS步长固定</div>',
                        unsafe_allow_html=True)
            bess_stp = _BESS_STEP

        # Snap inputs to 5 MWh multiples
        bess_min = _snap_bess(bess_min)
        bess_max = _snap_bess(bess_max)

        pv_range   = np.arange(pv_min,   pv_max   + pv_stp,   pv_stp)
        bess_range = np.arange(bess_min, bess_max + bess_stp, bess_stp)
        n_combos   = len(pv_range) * len(bess_range)

        st.markdown(
            f"搜索组合数 / Combinations: **{n_combos}** "
            f"(PV {len(pv_range)} × BESS {len(bess_range)})"
        )
        if n_combos > 200:
            st.markdown('<div class="warning-box">⚠️ >200 combinations — may be slow. Increase PV step size to reduce / 建议增大 PV 步长</div>',
                        unsafe_allow_html=True)

        if st.button("🚀 开始寻优 / Start Optimization", type="primary", use_container_width=True):
            if n_combos > 500:
                st.error("❌ Exceeds 500-combination limit — please increase PV step size / 超过500组合上限，请增大 PV 步长")
            else:
                opt_pvgis = get_pvgis_data(
                    st.session_state.lat, st.session_state.lon,
                    max(float(pv_max), 1.0),
                    st.session_state.pv_loss, st.session_state.tilt, st.session_state.azimuth,
                )
                pv_zar_k, bess_zar_k = get_capex_zar()
                params_opt = {
                    "pv_capex_per_kwp":   pv_zar_k,
                    "bess_capex_per_kwh": bess_zar_k,
                    "pv_opex_per_kwp":    st.session_state.pv_opex_per_kwp,
                    "bess_opex_per_kwh":  st.session_state.bess_opex_per_kwh,
                    "tariff_escalation":  st.session_state.tariff_escalation,
                    "discount_rate":      st.session_state.discount_rate,
                    "tax_rate":           st.session_state.tax_rate,
                    "pv_degradation":     st.session_state.pv_degradation,
                }
                # C倍率由选择器决定，在不同容量下等比例缩放功率
                c_actual = C_RATE_OPTIONS[st.session_state.c_rate_label]

                prog = st.progress(0)
                stat = st.empty()
                results_opt = []
                done = 0

                for pv_o in pv_range:
                    for bess_o in bess_range:
                        scale = pv_o / max(float(pv_max), 1.0)
                        pvgis_s = {
                            **opt_pvgis,
                            "monthly_kwh": [v * scale for v in opt_pvgis["monthly_kwh"]],
                            "annual_kwh":        opt_pvgis["annual_kwh"] * scale,
                            "winter_daily_kwh":  opt_pvgis["winter_daily_kwh"] * scale,
                            "summer_daily_kwh":  opt_pvgis["summer_daily_kwh"] * scale,
                        }
                        try:
                            d_o = run_8760_dispatch(
                                pv_kwp=pv_o, bess_kwh=bess_o,
                                bess_kw=bess_o * c_actual,
                                load_peak_kw=st.session_state.load_peak_kw,
                                load_std_kw=st.session_state.load_std_kw,
                                load_offpeak_kw=st.session_state.load_offpeak_kw,
                                rte=st.session_state.rte,
                                dod=st.session_state.dod,
                                pvgis_data=pvgis_s,
                            )
                            eol_o, ac_o = compute_bess_eol(
                                d_o["tot_throughput_kWh"], bess_o,
                                int(st.session_state.bess_cycles), st.session_state.dod,
                            )
                            fin_o = run_25yr_financial_model(
                                dispatch_yr1=d_o, pv_kwp=pv_o, bess_kwh=bess_o,
                                eol_years=eol_o, params=params_opt,
                                annual_cycles=ac_o,
                            )
                            cap_o = pv_o * pv_zar_k + bess_o * bess_zar_k
                            npv_o, irr_o = compute_npv_irr(fin_o, cap_o, params_opt["discount_rate"])
                            results_opt.append({
                                "PV (kWp)": pv_o, "BESS (kWh)": bess_o,
                                "CAPEX (ZAR)": cap_o, "NPV (ZAR)": npv_o,
                                "IRR (%)": irr_o, "EoL (yr)": eol_o,
                                "Annual Cycles": ac_o,
                                "Yr1 Saving (ZAR)": d_o["annual_saving_ZAR"],
                            })
                        except Exception:
                            pass
                        done += 1
                        prog.progress(done / n_combos)
                        if done % 5 == 0:
                            stat.text(f"⚙️ {done}/{n_combos}")

                prog.progress(1.0)
                stat.text("✅ Optimisation complete! / 寻优完成")

                if results_opt:
                    import plotly.graph_objects as go
                    opt_df = pd.DataFrame(results_opt)
                    best = opt_df.loc[opt_df["NPV (ZAR)"].idxmax()]

                    st.markdown("#### 🏆 最优配置 / Best Configuration")
                    bc1, bc2, bc3, bc4 = st.columns(4)
                    with bc1:
                        st.markdown(f"""<div class="metric-card">
                            <div class="metric-label">最优PV Optimal PV</div>
                            <div class="metric-value">{best['PV (kWp)']:.0f}</div>
                            <div class="metric-unit">kWp</div></div>""", unsafe_allow_html=True)
                    with bc2:
                        st.markdown(f"""<div class="metric-card">
                            <div class="metric-label">最优BESS Optimal BESS</div>
                            <div class="metric-value">{best['BESS (kWh)']:.0f}</div>
                            <div class="metric-unit">kWh ({best['BESS (kWh)']*c_actual:.0f}kW)</div></div>""",
                            unsafe_allow_html=True)
                    with bc3:
                        st.markdown(f"""<div class="metric-card">
                            <div class="metric-label">最优NPV Best NPV</div>
                            <div class="metric-value" style="color:var(--primary)">R{best['NPV (ZAR)']/1e6:.2f}M</div>
                            <div class="metric-unit">ZAR</div></div>""", unsafe_allow_html=True)
                    with bc4:
                        st.markdown(f"""<div class="metric-card">
                            <div class="metric-label">最优IRR Best IRR</div>
                            <div class="metric-value">{best['IRR (%)']:.1f}%</div>
                            <div class="metric-unit">Project IRR</div></div>""", unsafe_allow_html=True)

                    # NPV 热力图
                    st.markdown("#### 🗺️ NPV 热力图 / NPV Heatmap")
                    pivot = opt_df.pivot_table(index="BESS (kWh)", columns="PV (kWp)", values="NPV (ZAR)")
                    fig_h = go.Figure(data=go.Heatmap(
                        z=pivot.values / 1e6, x=pivot.columns, y=pivot.index,
                        colorscale=[[0,"#FF4444"],[0.5,"#111827"],[1,"#00E5A0"]],
                        colorbar=dict(title="NPV (M ZAR)"),
                        text=[[f"R{v:.1f}M" for v in row] for row in pivot.values / 1e6],
                        texttemplate="%{text}", textfont={"size": 8},
                    ))
                    fig_h.add_trace(go.Scatter(
                        x=[best["PV (kWp)"]], y=[best["BESS (kWh)"]],
                        mode="markers",
                        marker=dict(symbol="star", size=14, color="white",
                                    line=dict(color="#FF6B35", width=2)),
                        name="★ Optimal",
                    ))
                    fig_h.update_layout(
                        paper_bgcolor="#0A0E1A", plot_bgcolor="#111827",
                        font=dict(color="#E8ECF0", family="IBM Plex Mono"),
                        xaxis=dict(title="PV (kWp)", gridcolor="#2D3748"),
                        yaxis=dict(title="BESS (kWh)", gridcolor="#2D3748"),
                        height=480, margin=dict(l=10, r=10, t=20, b=10),
                    )
                    st.plotly_chart(fig_h, use_container_width=True)

                    st.markdown("#### 📊 全部寻优结果 / Full Results")
                    st.dataframe(opt_df.sort_values("NPV (ZAR)", ascending=False),
                                 use_container_width=True, height=380)

# ─────────────────────────────────────────────────────────────
# 页脚 / Footer
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:var(--text-dim); font-family:'IBM Plex Mono',monospace;
            font-size:0.68rem; padding:0.8rem 0;">
    Powered by Huawei SA Digital Power — BD Kevin Yi &nbsp;|&nbsp;
    <a href="https://wa.me/27834976899?text=Hi%20Kevin%2C%20I%20would%20like%20more%20info%20on%20BTM%20PV%2BBESS%20solutions"
       target="_blank"
       style="color:#25D366; text-decoration:none; font-weight:600;">
       💬 WhatsApp: 083 497 6899
    </a>
    &nbsp;|&nbsp; SA Megaflex · PVGIS · Section 12B · 8760H Dispatch · Weekday/Weekend TOU
</div>
""", unsafe_allow_html=True)
