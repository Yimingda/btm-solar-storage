"""
scenario_select.py — Post-login landing page: language + scenario selector
BTM PV+BESS Financial Modelling System
"""
from __future__ import annotations

import streamlit as st
from auth import get_current_user, logout


# ── Shared CSS ────────────────────────────────────────────────────────────────

_LANDING_CSS = """
<style>
/* ── Scenario landing page ── */
.sc-page {
    max-width: 820px;
    margin: 0 auto;
    padding: 0 16px 40px;
}
.sc-brand {
    text-align: center;
    padding: 28px 0 18px;
}
.sc-brand .sc-logo   { font-size: 2.2rem; }
.sc-brand .sc-appname {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.45rem; font-weight: 700;
    color: #00E5A0; letter-spacing: 0.05em;
    margin: 6px 0 3px;
}
.sc-brand .sc-tagline { font-size: 0.8rem; color: #8B95A3; }

.sc-welcome {
    text-align: center;
    padding: 0 0 22px;
}
.sc-welcome .sc-hi  { font-size: 1.05rem; color: #E8ECF0; }
.sc-welcome .sc-sub { font-size: 0.82rem; color: #8B95A3; margin-top: 3px; }

/* Scenario cards */
.sc-card {
    border: 2px solid #2D3748;
    border-radius: 12px;
    background: #111827;
    padding: 22px 20px 16px;
    min-height: 310px;
    box-sizing: border-box;
    position: relative;
}
.sc-card.btm     { border-color: #00E5A0; }
.sc-card.wheeling { border-color: #4ECDC4; }

.sc-badge {
    display: inline-block;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.68rem;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
}
.sc-badge.btm     { background: #0d2b1e; color: #00E5A0; }
.sc-badge.wheeling { background: #0d2424; color: #4ECDC4; }

.sc-icon    { font-size: 2rem; margin-bottom: 6px; }
.sc-title   { font-size: 1.12rem; font-weight: 700; color: #E8ECF0; margin-bottom: 4px; }
.sc-sub     { font-size: 0.8rem;  color: #8B95A3;  margin-bottom: 14px; }
.sc-feature { font-size: 0.78rem; color: #B0BEC5;  margin: 3px 0; }

/* Wheeling placeholder page */
.whl-hero {
    text-align: center;
    padding: 32px 0 24px;
}
.whl-hero .whl-icon    { font-size: 2.8rem; }
.whl-hero .whl-title   {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.35rem; font-weight: 700;
    color: #4ECDC4; margin: 8px 0 4px;
}
.whl-hero .whl-tagline { font-size: 0.82rem; color: #8B95A3; }

.whl-scope {
    border: 1px solid #2D3748;
    border-radius: 8px;
    background: #111827;
    padding: 18px 20px;
    margin-bottom: 14px;
}
.whl-scope .ws-title {
    font-size: 0.88rem; font-weight: 600; color: #4ECDC4;
    margin-bottom: 10px;
}
.whl-scope .ws-item { font-size: 0.82rem; color: #B0BEC5; margin: 4px 0; }

.wip-banner {
    background: #1a2a1a;
    border: 1px solid #00E5A0;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 0.8rem;
    color: #A8D5A2;
    text-align: center;
    margin: 10px 0 18px;
}
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
    st.markdown(_LANDING_CSS, unsafe_allow_html=True)

    # ── Top bar: user info (left) + lang selector (right) ──────────────────
    _top_l, _top_r = st.columns([8, 2])
    with _top_l:
        _u = get_current_user()
        if _u:
            _name = _u.get("full_name") or _u.get("email", "User")
            _tier = {"free": "🆓", "pro": "🔵", "admin": "🔴"}.get(
                _u.get("tier", "free"), "🆓")
            st.markdown(
                f"<div style='font-size:0.85em;padding-top:6px'>"
                f"👤 <b>{_name}</b> &nbsp;{_tier} &nbsp;"
                f"<span style='color:#667;font-size:0.9em'>"
                f"· <a href='#' style='color:#667;text-decoration:none'></span></div>",
                unsafe_allow_html=True,
            )
    with _top_r:
        _lang_idx = 0 if st.session_state.get("lang", "bilingual") == "bilingual" else 1
        _lo = st.radio(
            "🌐", options=["双语", "EN"],
            index=_lang_idx, horizontal=True,
            key="lang_radio", label_visibility="collapsed",
        )
        st.session_state["lang"] = "bilingual" if _lo == "双语" else "english"
    _en = st.session_state.get("lang") == "english"

    # ── Centred content ─────────────────────────────────────────────────────
    _, _centre, _ = st.columns([1, 5, 1])
    with _centre:

        # Brand header
        st.markdown(f"""
<div class="sc-brand">
  <div class="sc-logo">⚡</div>
  <div class="sc-appname">BTM Solar+BESS Platform</div>
  <div class="sc-tagline">
    {"Professional Solar Energy Financial Modelling System"
     if _en else "专业级光储财务测算平台 · Professional Solar Energy Financial Modelling"}
  </div>
</div>""", unsafe_allow_html=True)

        # Welcome
        if _u:
            _name = _u.get("full_name") or _u.get("email", "User")
            st.markdown(f"""
<div class="sc-welcome">
  <div class="sc-hi">👋 {"Welcome back," if _en else "欢迎回来，"} <b>{_name}</b></div>
  <div class="sc-sub">{"Please select a scenario to continue." if _en else "请选择分析场景继续"}</div>
</div>""", unsafe_allow_html=True)

        # ── Two scenario cards ──────────────────────────────────────────────
        _c1, _c2 = st.columns(2, gap="large")

        # ── Card 1: BTM ─────────────────────────────────────────────────────
        with _c1:
            if _en:
                _btm_features = [
                    "20-Year Financial Model",
                    "8760h Physical Dispatch Engine",
                    "Section 12B / Straight-line Depreciation",
                    "Megaflex · Miniflex TOU Tariffs 2025/26",
                    "NPV · IRR · Simple Payback",
                    "AI System Size Optimisation",
                    "Excel Report Export",
                ]
                _btm_sub = "Behind-the-Meter Self-Consumption"
            else:
                _btm_features = [
                    "20 年逐年财务报表",
                    "8760 小时物理调度引擎",
                    "Section 12B / 普通折旧减税模型",
                    "Megaflex · Miniflex 分时电价 2025/26",
                    "NPV · IRR · 投资回收期分析",
                    "AI 系统容量寻优",
                    "Excel 报表一键导出",
                ]
                _btm_sub = "企业侧自发自用光储系统"

            _feat_html = "".join(
                f'<div class="sc-feature">✓ {f}</div>' for f in _btm_features
            )
            st.markdown(f"""
<div class="sc-card btm">
  <div class="sc-badge btm">SCENARIO 1</div>
  <div class="sc-icon">🔋</div>
  <div class="sc-title">{"BTM PV+BESS" if _en else "BTM 光储方案"}</div>
  <div class="sc-sub">{_btm_sub}</div>
  {_feat_html}
</div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "▶ Enter BTM Model" if _en else "▶ 进入 BTM 模型",
                key="sc_btn_btm",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["_scenario"] = "btm"
                st.rerun()

        # ── Card 2: Wheeling ────────────────────────────────────────────────
        with _c2:
            if _en:
                _whl_features = [
                    "Wheeling Fee & Network Charge Modelling",
                    "Generator-side Revenue Analysis",
                    "Off-taker Cost vs Conventional Tariff",
                    "Municipal / Eskom Tariff Integration",
                    "20-Year Financial Model (BTM Framework)",
                    "NPV · IRR for Generator & Off-taker",
                    "Excel Report Export",
                ]
                _whl_sub = "Grid-Wheeled Renewable Power Trading"
            else:
                _whl_features = [
                    "过网费 / 网络使用费建模",
                    "发电侧收益分析",
                    "用电侧成本 vs 传统电价对比",
                    "市政 / Eskom 电价接入",
                    "20 年财务模型（基于 BTM 框架）",
                    "发电方 & 用电方双侧 NPV · IRR",
                    "Excel 报表导出",
                ]
                _whl_sub = "远距离过网发电交易方案"

            _feat_html = "".join(
                f'<div class="sc-feature">✓ {f}</div>' for f in _whl_features
            )
            st.markdown(f"""
<div class="sc-card wheeling">
  <div class="sc-badge wheeling">SCENARIO 2</div>
  <div class="sc-icon">⚡</div>
  <div class="sc-title">{"Wheeling" if _en else "Wheeling 过网方案"}</div>
  <div class="sc-sub">{_whl_sub}</div>
  {_feat_html}
</div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "▶ Enter Wheeling Model" if _en else "▶ 进入 Wheeling 模型",
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
                "Sign Out" if _en else "退出登录",
                key="sc_logout_btn",
                use_container_width=True,
                help="Sign out / 退出账号",
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
    st.markdown(_LANDING_CSS, unsafe_allow_html=True)
    _en = st.session_state.get("lang") == "english"

    # ── Top bar: back + lang ────────────────────────────────────────────────
    _tb1, _tb2, _tb3 = st.columns([2, 6, 2])
    with _tb1:
        if st.button(
            "◀ Scenarios" if _en else "◀ 返回场景",
            key="whl_back_btn",
        ):
            st.session_state.pop("_scenario", None)
            st.rerun()
    with _tb3:
        _lang_idx = 0 if st.session_state.get("lang", "bilingual") == "bilingual" else 1
        _lo = st.radio(
            "🌐", options=["双语", "EN"],
            index=_lang_idx, horizontal=True,
            key="lang_radio", label_visibility="collapsed",
        )
        st.session_state["lang"] = "bilingual" if _lo == "双语" else "english"
        _en = st.session_state.get("lang") == "english"

    # ── Hero ────────────────────────────────────────────────────────────────
    st.markdown(f"""
<div class="whl-hero">
  <div class="whl-icon">⚡</div>
  <div class="whl-title">{"Wheeling Model" if _en else "Wheeling 过网方案"}</div>
  <div class="whl-tagline">
    {"Grid-Wheeled Renewable Power Trading · Financial Analysis Platform"
     if _en else "远距离过网发电交易 · 财务测算平台"}
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown(
        f'<div class="wip-banner">🚧 &nbsp;'
        f'{"Module under development — framework and scope defined below."
           if _en else "模块开发中 — 以下展示功能框架与设计范围"}'
        f'&nbsp; 🚧</div>',
        unsafe_allow_html=True,
    )

    # ── Scope cards ─────────────────────────────────────────────────────────
    _s1, _s2 = st.columns(2, gap="medium")

    with _s1:
        st.markdown(f"""
<div class="whl-scope">
  <div class="ws-title">{"⚡ Generator Side / 发电侧" if _en else "⚡ 发电侧"}</div>
  <div class="ws-item">• {"PV system sizing & yield (PVGIS)" if _en else "光伏装机及发电量（PVGIS）"}</div>
  <div class="ws-item">• {"BESS with wheeling dispatch strategy" if _en else "储能系统（适配过网调度策略）"}</div>
  <div class="ws-item">• {"Wheeling tariff (ZAR/kWh) agreement" if _en else "过网电价协议（ZAR/kWh）"}</div>
  <div class="ws-item">• {"Network use-of-system (NuoS) charges" if _en else "网络使用费（NuoS）"}</div>
  <div class="ws-item">• {"Section 12B / depreciation tax shield" if _en else "S12B / 折旧减税计算"}</div>
  <div class="ws-item">• {"20-yr revenue model: NPV · IRR" if _en else "20 年收益模型：NPV · IRR"}</div>
</div>""", unsafe_allow_html=True)

    with _s2:
        st.markdown(f"""
<div class="whl-scope">
  <div class="ws-title">{"🏭 Off-taker Side / 用电侧" if _en else "🏭 用电侧"}</div>
  <div class="ws-item">• {"C&I load profile (kWh/h)" if _en else "工商业负荷曲线输入（kWh/h）"}</div>
  <div class="ws-item">• {"Conventional grid tariff baseline" if _en else "传统电网电价基准"}</div>
  <div class="ws-item">• {"Wheeled energy cost vs tariff savings" if _en else "过网电价成本 vs 传统电费节省"}</div>
  <div class="ws-item">• {"Municipal or Eskom tariff options" if _en else "市政 / Eskom 电价选择"}</div>
  <div class="ws-item">• {"Net benefit analysis (20yr)" if _en else "净收益分析（20 年期）"}</div>
  <div class="ws-item">• {"Excel report for both sides" if _en else "双侧 Excel 财务报表"}</div>
</div>""", unsafe_allow_html=True)

    _s3, _s4 = st.columns(2, gap="medium")

    with _s3:
        st.markdown(f"""
<div class="whl-scope">
  <div class="ws-title">{"📐 Shared Framework / 共用模块" if _en else "📐 共用模块（源自 BTM）"}</div>
  <div class="ws-item">• {"8760h physical dispatch engine" if _en else "8760 小时物理调度引擎"}</div>
  <div class="ws-item">• {"PVGIS solar yield integration" if _en else "PVGIS 太阳辐射数据接口"}</div>
  <div class="ws-item">• {"Huawei LUNA SOH degradation tables" if _en else "华为 LUNA 电池 SOH 退化表"}</div>
  <div class="ws-item">• {"Discount rate · escalation · tax model" if _en else "折现率 · 电价涨幅 · 税务模型"}</div>
  <div class="ws-item">• {"Project snapshot management" if _en else "项目快照管理"}</div>
</div>""", unsafe_allow_html=True)

    with _s4:
        st.markdown(f"""
<div class="whl-scope">
  <div class="ws-title">{"📋 Planned Outputs / 规划输出" if _en else "📋 规划输出"}</div>
  <div class="ws-item">• {"Wheeling agreement term sheet template" if _en else "过网协议条款表模板"}</div>
  <div class="ws-item">• {"Dual-party financial summary" if _en else "双方财务摘要页"}</div>
  <div class="ws-item">• {"Sensitivity: wheeling price vs savings" if _en else "敏感性：过网电价 vs 节省金额"}</div>
  <div class="ws-item">• {"NERSA / municipal licensing checklist" if _en else "NERSA / 市政许可证清单"}</div>
  <div class="ws-item">• {"Excel workbook (6-sheet structure)" if _en else "Excel 工作簿（6 页结构）"}</div>
</div>""", unsafe_allow_html=True)

    # ── Placeholder tabs ─────────────────────────────────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    _tab_labels = (
        ["⚙️ Parameters", "📊 Results", "📋 Financial Model", "📁 Export"]
        if _en else
        ["⚙️ 参数输入", "📊 计算结果", "📋 财务模型", "📁 导出报表"]
    )
    _t1, _t2, _t3, _t4 = st.tabs(_tab_labels)
    with _t1:
        st.info("🚧 " + ("Parameter inputs coming soon." if _en else "参数输入界面开发中"))
    with _t2:
        st.info("🚧 " + ("Results dashboard coming soon." if _en else "结果仪表盘开发中"))
    with _t3:
        st.info("🚧 " + ("20-year financial table coming soon." if _en else "20 年财务报表开发中"))
    with _t4:
        st.info("🚧 " + ("Excel export coming soon." if _en else "Excel 导出开发中"))
