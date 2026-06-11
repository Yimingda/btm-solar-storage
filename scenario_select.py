"""
scenario_select.py — Post-login landing page: scenario selector
BTM PV+BESS Financial Modelling System
"""
from __future__ import annotations

import streamlit as st
from auth import logout


# ── Shared CSS ────────────────────────────────────────────────────────────────

def _landing_css(light: bool = False) -> str:
    """Return landing-page CSS tuned for dark (default) or light theme."""
    if light:
        card_bg      = "#FFFFFF"
        card_border  = "#CBD5E0"
        sc_title     = "#1A202C"
        sc_sub       = "#4A5568"
        sc_feat      = "#374151"
        whl_tagline  = "#4A5568"
        scope_bg     = "#FFFFFF"
        scope_border = "#CBD5E0"
        scope_item   = "#374151"
        wip_bg       = "#F0FFF4"
        wip_border   = "#00A870"
        wip_color    = "#065F46"
    else:
        card_bg      = "#111827"
        card_border  = "#2D3748"
        sc_title     = "#E8ECF0"
        sc_sub       = "#8B95A3"
        sc_feat      = "#B0BEC5"
        whl_tagline  = "#8B95A3"
        scope_bg     = "#111827"
        scope_border = "#2D3748"
        scope_item   = "#B0BEC5"
        wip_bg       = "#1a2a1a"
        wip_border   = "#00E5A0"
        wip_color    = "#A8D5A2"

    return f"""<style>
/* ── Scenario landing page — {{'light' if light else 'dark'}} ── */

div[data-testid="stHorizontalBlock"]:first-of-type {{
    background: transparent !important;
    border-bottom: none !important;
    padding: 0 !important;
    margin-bottom: 0 !important;
}}
div[data-testid="stHorizontalBlock"]:first-of-type div[data-testid="stColumn"] {{
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}}

.sc-page {{
    max-width: 820px;
    margin: 0 auto;
    padding: 0 16px 40px;
}}

.sc-card {{
    border: 2px solid {card_border};
    border-radius: 12px;
    background: {card_bg};
    padding: 22px 20px 16px;
    min-height: 310px;
    box-sizing: border-box;
    position: relative;
}}
.sc-card.btm      {{ border-color: #00E5A0; }}
.sc-card.wheeling {{ border-color: #4ECDC4; }}

.sc-badge {{
    display: inline-block;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.68rem;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
}}
.sc-badge.btm      {{ background: {'rgba(0,168,112,0.12)' if light else '#0d2b1e'}; color: {'#059669' if light else '#00E5A0'}; }}
.sc-badge.wheeling {{ background: {'rgba(78,205,196,0.12)' if light else '#0d2424'}; color: {'#0E7490' if light else '#4ECDC4'}; }}

.sc-icon    {{ font-size: 2rem; margin-bottom: 6px; }}
.sc-title   {{ font-size: 1.12rem; font-weight: 700; color: {sc_title}; margin-bottom: 4px; }}
.sc-sub     {{ font-size: 0.8rem;  color: {sc_sub};  margin-bottom: 14px; }}
.sc-feature {{ font-size: 0.78rem; color: {sc_feat}; margin: 3px 0; }}

.whl-hero {{
    text-align: center;
    padding: 32px 0 24px;
}}
.whl-hero .whl-icon    {{ font-size: 2.8rem; }}
.whl-hero .whl-title   {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.35rem; font-weight: 700;
    color: {'#0E7490' if light else '#4ECDC4'}; margin: 8px 0 4px;
}}
.whl-hero .whl-tagline {{ font-size: 0.82rem; color: {whl_tagline}; }}

.whl-scope {{
    border: 1px solid {scope_border};
    border-radius: 8px;
    background: {scope_bg};
    padding: 18px 20px;
    margin-bottom: 14px;
}}
.whl-scope .ws-title {{
    font-size: 0.88rem; font-weight: 600;
    color: {'#0E7490' if light else '#4ECDC4'};
    margin-bottom: 10px;
}}
.whl-scope .ws-item {{ font-size: 0.82rem; color: {scope_item}; margin: 4px 0; }}

.wip-banner {{
    background: {wip_bg};
    border: 1px solid {wip_border};
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 0.8rem;
    color: {wip_color};
    text-align: center;
    margin: 10px 0 18px;
}}
</style>
"""


# ════════════════════════════════════════════════════════════════════════════
# Scenario selector landing page
# ════════════════════════════════════════════════════════════════════════════

def render_scenario_selector() -> None:
    """
    Full-page scenario selection shown right after login.
    Writes st.session_state['_scenario'] = 'btm' | 'wheeling' then reruns.
    """
    st.markdown(_landing_css(st.session_state.get("_light_mode", False)),
                unsafe_allow_html=True)

    # ── Centred content ─────────────────────────────────────────────────────
    _, _centre, _ = st.columns([1, 5, 1])
    with _centre:
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # ── Two scenario cards ──────────────────────────────────────────────
        _c1, _c2 = st.columns(2, gap="large")

        # ── Card 1: BTM ─────────────────────────────────────────────────────
        with _c1:
            _btm_features = [
                "20-Year Financial Model",
                "8760h Physical Dispatch Engine",
                "Section 12B / Straight-line Depreciation",
                "Megaflex · Miniflex TOU Tariffs 2025/26",
                "NPV · IRR · Simple Payback",
                "AI System Size Optimisation",
                "Excel Report Export",
            ]
            _feat_html = "".join(
                f'<div class="sc-feature">✓ {f}</div>' for f in _btm_features
            )
            st.markdown(f"""
<div class="sc-card btm">
  <div class="sc-badge btm">SCENARIO 1</div>
  <div class="sc-icon">🔋</div>
  <div class="sc-title">BTM PV+BESS</div>
  <div class="sc-sub">Behind-the-Meter Self-Consumption</div>
  {_feat_html}
</div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "▶ Enter BTM Model",
                key="sc_btn_btm",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["_scenario"] = "btm"
                st.rerun()

        # ── Card 2: Wheeling ────────────────────────────────────────────────
        with _c2:
            _whl_features = [
                "Wheeling Fee & Network Charge Modelling",
                "Generator-side Revenue Analysis",
                "Off-taker Cost vs Conventional Tariff",
                "Municipal / Eskom Tariff Integration",
                "20-Year Financial Model (BTM Framework)",
                "NPV · IRR for Generator & Off-taker",
                "Excel Report Export",
            ]
            _feat_html = "".join(
                f'<div class="sc-feature">✓ {f}</div>' for f in _whl_features
            )
            st.markdown(f"""
<div class="sc-card wheeling">
  <div class="sc-badge wheeling">SCENARIO 2</div>
  <div class="sc-icon">⚡</div>
  <div class="sc-title">Wheeling</div>
  <div class="sc-sub">Grid-Wheeled Renewable Power Trading</div>
  {_feat_html}
</div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "▶ Enter Wheeling Model",
                key="sc_btn_whl",
                use_container_width=True,
            ):
                st.session_state["_scenario"] = "wheeling"
                st.rerun()

        # ── Footer: logout ──────────────────────────────────────────────────
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        _, _fc, _ = st.columns([3, 2, 3])
        with _fc:
            if st.button(
                "Sign Out",
                key="sc_logout_btn",
                use_container_width=True,
                help="Sign out",
            ):
                logout()


# ════════════════════════════════════════════════════════════════════════════
# Wheeling placeholder  (Scenario 2 stub — to be developed)
# ════════════════════════════════════════════════════════════════════════════

def render_wheeling_placeholder() -> None:
    """
    Wheeling scenario page — structured placeholder pending full build-out.
    Shows intended module scope and framework tabs.
    """
    st.markdown(_landing_css(st.session_state.get("_light_mode", False)),
                unsafe_allow_html=True)

    # ── Top bar: back ────────────────────────────────────────────────────────
    _tb1, _tb2 = st.columns([2, 8])
    with _tb1:
        if st.button(
            "◀ Scenarios",
            key="whl_back_btn",
        ):
            st.session_state.pop("_scenario", None)
            st.rerun()

    # ── Hero ────────────────────────────────────────────────────────────────
    st.markdown("""
<div class="whl-hero">
  <div class="whl-icon">⚡</div>
  <div class="whl-title">Wheeling Model</div>
  <div class="whl-tagline">Grid-Wheeled Renewable Power Trading · Financial Analysis Platform</div>
</div>""", unsafe_allow_html=True)

    st.markdown(
        '<div class="wip-banner">🚧 &nbsp;'
        'Module under development — framework and scope defined below.'
        '&nbsp; 🚧</div>',
        unsafe_allow_html=True,
    )

    # ── Scope cards ─────────────────────────────────────────────────────────
    _s1, _s2 = st.columns(2, gap="medium")

    with _s1:
        st.markdown("""
<div class="whl-scope">
  <div class="ws-title">⚡ Generator Side</div>
  <div class="ws-item">• PV system sizing & yield (PVGIS)</div>
  <div class="ws-item">• BESS with wheeling dispatch strategy</div>
  <div class="ws-item">• Wheeling tariff (ZAR/kWh) agreement</div>
  <div class="ws-item">• Network use-of-system (NuoS) charges</div>
  <div class="ws-item">• Section 12B / depreciation tax shield</div>
  <div class="ws-item">• 20-yr revenue model: NPV · IRR</div>
</div>""", unsafe_allow_html=True)

    with _s2:
        st.markdown("""
<div class="whl-scope">
  <div class="ws-title">🏭 Off-taker Side</div>
  <div class="ws-item">• C&I load profile (kWh/h)</div>
  <div class="ws-item">• Conventional grid tariff baseline</div>
  <div class="ws-item">• Wheeled energy cost vs tariff savings</div>
  <div class="ws-item">• Municipal or Eskom tariff options</div>
  <div class="ws-item">• Net benefit analysis (20yr)</div>
  <div class="ws-item">• Excel report for both sides</div>
</div>""", unsafe_allow_html=True)

    _s3, _s4 = st.columns(2, gap="medium")

    with _s3:
        st.markdown("""
<div class="whl-scope">
  <div class="ws-title">📐 Shared Framework</div>
  <div class="ws-item">• 8760h physical dispatch engine</div>
  <div class="ws-item">• PVGIS solar yield integration</div>
  <div class="ws-item">• Huawei LUNA SOH degradation tables</div>
  <div class="ws-item">• Discount rate · escalation · tax model</div>
  <div class="ws-item">• Project snapshot management</div>
</div>""", unsafe_allow_html=True)

    with _s4:
        st.markdown("""
<div class="whl-scope">
  <div class="ws-title">📋 Planned Outputs</div>
  <div class="ws-item">• Wheeling agreement term sheet template</div>
  <div class="ws-item">• Dual-party financial summary</div>
  <div class="ws-item">• Sensitivity: wheeling price vs savings</div>
  <div class="ws-item">• NERSA / municipal licensing checklist</div>
  <div class="ws-item">• Excel workbook (6-sheet structure)</div>
</div>""", unsafe_allow_html=True)

    # ── Placeholder tabs ─────────────────────────────────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    _tab_labels = ["⚙️ Parameters", "📊 Results", "📋 Financial Model", "📁 Export"]
    _t1, _t2, _t3, _t4 = st.tabs(_tab_labels)
    with _t1:
        st.info("🚧 Parameter inputs coming soon.")
    with _t2:
        st.info("🚧 Results dashboard coming soon.")
    with _t3:
        st.info("🚧 20-year financial table coming soon.")
    with _t4:
        st.info("🚧 Excel export coming soon.")
