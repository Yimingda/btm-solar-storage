"""
snapshots.py — 快照管理面板
BTM PV+BESS Financial Modelling System

Renders the snapshot panel inside the right-column scroll container.
All DB operations go through db.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st

from db import (get_snapshots, get_snapshot_full, save_snapshot,
                update_snapshot, delete_snapshot)
from auth import get_current_user, is_pro

# ── Keys that define a complete project state ────────────────────────────────
# Mirrors DEFAULT_PARAMS in app.py — any key present in session_state is saved.
_SAVE_KEYS = [
    "lat", "lon", "tilt", "azimuth", "pv_loss",
    "pv_kwp", "bess_kwh", "c_rate_label",
    "load_peak_kw", "load_std_kw", "load_offpeak_kw",
    "rte", "bess_cycles", "dod",
    "forex_usd_zar", "pv_usd_per_w", "bess_usd_per_wh",
    "pv_opex_per_kwp", "bess_opex_per_kwh",
    "tariff_escalation", "discount_rate", "tax_rate", "pv_degradation",
    "tariff_mode",
    "w_morning_peak", "w_evening_peak", "w_standard", "w_off_peak",
    "s_morning_peak", "s_evening_peak", "s_standard", "s_off_peak",
    "lang",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _default_name() -> str:
    """Generate default snapshot name from current session state."""
    pv   = st.session_state.get("pv_kwp",   0) or 0
    bess = st.session_state.get("bess_kwh", 0) or 0
    if bess > 0:
        return f"{pv:.0f}kWp + {bess:.0f}kWh"
    return f"{pv:.0f}kWp PV Only"


def get_params_to_save() -> dict:
    """Collect all saveable params from session_state."""
    params = {}
    for key in _SAVE_KEYS:
        val = st.session_state.get(key)
        if val is not None:
            try:
                json.dumps(val)   # verify JSON-serialisable
                params[key] = val
            except (TypeError, ValueError):
                params[key] = str(val)
    return params


def get_results_summary() -> dict:
    """Extract lightweight results summary for snapshot list display."""
    res = st.session_state.get("results")
    if not res:
        return {}
    return {
        "npv":     round(res.get("npv", 0), 0),
        "irr":     round(res.get("irr", 0), 2),
        "payback": round(res.get("simple_payback", 0), 2),
    }


def restore_snapshot(params: dict) -> None:
    """Load all snapshot params back into session_state."""
    for key, val in params.items():
        st.session_state[key] = val
    # Clear stale results so user re-runs the simulation
    for k in ("results", "fin_df", "hourly_df"):
        st.session_state[k] = None


# ════════════════════════════════════════════════════════════════════════════
# Main panel — called from app.py inside _scroll container
# ════════════════════════════════════════════════════════════════════════════

def render_snapshot_panel() -> None:
    user = get_current_user()
    if not user:
        return

    user_id = user["id"]
    limit   = user.get("snapshot_limit", 3)
    tier    = user.get("tier", "free")

    snapshots = get_snapshots(user_id)
    count     = len(snapshots)

    _tier_icon = {"free": "🆓", "pro": "🔵", "admin": "🔴"}.get(tier, "🆓")
    limit_str  = "∞" if limit >= 999999 else str(limit)

    # ── Header row: title badge + collapse toggle + save button ──
    h1, h2, h3 = st.columns([5, 2, 2])
    with h1:
        st.markdown(
            f"**📂 快照** `{count}`**/**`{limit_str}` {_tier_icon}",
            unsafe_allow_html=True,
        )
    with h2:
        _expanded = st.session_state.get("_snap_expanded", True)
        if st.button("▲ 收起" if _expanded else "▼ 展开",
                     key="snap_toggle_btn", use_container_width=True):
            st.session_state["_snap_expanded"] = not _expanded
            st.rerun()
    with h3:
        if st.button("💾 保存", use_container_width=True, key="snap_save_btn",
                     type="primary"):
            if count >= limit:
                _show_limit_msg(tier, limit)
            else:
                st.session_state["_snap_save_open"]    = True
                st.session_state["_snap_default_name"] = _default_name()

    # ── Save dialog (inline) ──
    if st.session_state.get("_snap_save_open"):
        _render_save_dialog(user_id)

    # ── Collapsible snapshot list ──
    if not st.session_state.get("_snap_expanded", True):
        return

    if not snapshots:
        st.markdown(
            "<div style='color:#888;font-size:0.82em;text-align:center;"
            "padding:8px 0'>暂无快照 / No snapshots yet</div>",
            unsafe_allow_html=True,
        )
        return

    for snap in snapshots:
        _render_snapshot_item(snap)


# ── Save dialog ──────────────────────────────────────────────────────────────

def _render_save_dialog(user_id: str) -> None:
    default = st.session_state.get("_snap_default_name", _default_name())
    name = st.text_input(
        "快照名称 Snapshot Name",
        value=default,
        key="snap_name_input",
        placeholder="e.g. Site A · 100kWp+200kWh",
    )
    ok_col, cancel_col = st.columns(2)
    with ok_col:
        if st.button("✅ 保存 Save", type="primary",
                     use_container_width=True, key="snap_dialog_ok"):
            final = name.strip() or default
            result = save_snapshot(
                user_id=user_id,
                name=final,
                default_name=_default_name(),
                params=get_params_to_save(),
                results=get_results_summary(),
            )
            if result:
                st.toast(f"✅ 已保存 / Saved: {final}")
            _close_dialog()
    with cancel_col:
        if st.button("✖ 取消 Cancel", use_container_width=True,
                     key="snap_dialog_cancel"):
            _close_dialog()


def _close_dialog():
    for k in ("_snap_save_open", "_snap_default_name", "snap_name_input"):
        st.session_state.pop(k, None)
    st.rerun()


# ── Single snapshot item ──────────────────────────────────────────────────────

def _render_snapshot_item(snap: dict) -> None:
    snap_id = snap["id"]
    name    = snap["name"]
    default = snap.get("default_name") or name
    pinned  = snap.get("is_pinned", False)
    results = snap.get("results_json") or {}

    # Timestamp
    try:
        dt = datetime.fromisoformat(snap["updated_at"].replace("Z", "+00:00"))
        ts = dt.strftime("%m-%d %H:%M")
    except Exception:
        ts = ""

    # Result badge
    npv = results.get("npv", 0)
    irr = results.get("irr", 0)
    badge = f"NPV {npv/1e6:+.1f}M · IRR {irr:.1f}%" if npv else "未运算"

    pin_icon = "★ " if pinned else ""

    # ── Row: load button (wide) + ⋮ menu (narrow) ──
    load_col, menu_col = st.columns([11, 1])

    with load_col:
        if st.button(
            f"{pin_icon}{name}  ·  {badge}  ·  {ts}",
            key=f"snap_load_{snap_id}",
            use_container_width=True,
            help=f"点击加载 / Click to load · {default}",
        ):
            full = get_snapshot_full(snap_id)
            if full and full.get("params_json"):
                restore_snapshot(full["params_json"])
                st.toast(f"✅ 已加载: {name}")
                st.rerun()
            else:
                st.error("快照读取失败 / Failed to load")

    with menu_col:
        with st.popover("⋮", use_container_width=True):
            st.markdown(f"**{name}**")
            st.divider()

            # Pin / Unpin
            pin_lbl = "📍 取消置顶 Unpin" if pinned else "📌 置顶 Pin"
            if st.button(pin_lbl, key=f"pm_pin_{snap_id}",
                         use_container_width=True):
                update_snapshot(snap_id, is_pinned=not pinned)
                st.rerun()

            # Rename
            if st.button("✏️ 重命名 Rename", key=f"pm_ren_{snap_id}",
                         use_container_width=True):
                st.session_state[f"_ren_{snap_id}"] = True
                st.rerun()

            # Update config
            if st.button("♻️ 更新配置 Update", key=f"pm_upd_{snap_id}",
                         use_container_width=True,
                         help="用当前参数覆盖此快照 / Overwrite with current params"):
                update_snapshot(snap_id,
                                params_json=get_params_to_save(),
                                results_json=get_results_summary(),
                                default_name=_default_name())
                st.toast(f"✅ 已更新: {name}")
                st.rerun()

            st.divider()

            # Delete
            if st.button("🗑️ 删除 Delete", key=f"pm_del_{snap_id}",
                         use_container_width=True, type="primary"):
                st.session_state[f"_del_{snap_id}"] = True
                st.rerun()

    # ── Inline rename ──
    if st.session_state.get(f"_ren_{snap_id}"):
        new_name = st.text_input("新名称 New name", value=name,
                                  key=f"ren_inp_{snap_id}")
        rn1, rn2 = st.columns(2)
        with rn1:
            if st.button("✅ 确认", key=f"ren_ok_{snap_id}",
                         use_container_width=True, type="primary"):
                if new_name.strip():
                    update_snapshot(snap_id, name=new_name.strip())
                st.session_state.pop(f"_ren_{snap_id}", None)
                st.rerun()
        with rn2:
            if st.button("✖ 取消", key=f"ren_cancel_{snap_id}",
                         use_container_width=True):
                st.session_state.pop(f"_ren_{snap_id}", None)
                st.rerun()

    # ── Inline delete confirm ──
    if st.session_state.get(f"_del_{snap_id}"):
        st.warning(f"确认删除 '{name}'？")
        d1, d2 = st.columns(2)
        with d1:
            if st.button("✅ 确认删除", key=f"del_ok_{snap_id}",
                         type="primary", use_container_width=True):
                delete_snapshot(snap_id)
                st.session_state.pop(f"_del_{snap_id}", None)
                st.toast("🗑️ 已删除")
                st.rerun()
        with d2:
            if st.button("✖ 取消", key=f"del_cancel_{snap_id}",
                         use_container_width=True):
                st.session_state.pop(f"_del_{snap_id}", None)
                st.rerun()

    st.markdown(
        "<hr style='margin:2px 0; border-color:#2a2a4a'>",
        unsafe_allow_html=True,
    )


# ── Limit message ─────────────────────────────────────────────────────────────

def _show_limit_msg(tier: str, limit: int) -> None:
    if tier == "free":
        st.error(
            f"已达免费版快照上限 {limit} 个。"
            f"请联系管理员升级为 🔵 Pro 版（50个快照）。\n\n"
            f"Free tier limit ({limit} snapshots) reached. "
            f"Contact admin to upgrade to 🔵 Pro."
        )
    else:
        st.error(f"已达快照上限 {limit} 个 / Snapshot limit ({limit}) reached")
