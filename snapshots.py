"""
snapshots.py — 项目管理面板 / Project (Snapshot) Management Panel
BTM PV+BESS Financial Modelling System
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st

from db import (get_snapshots, get_snapshot_full, save_snapshot,
                update_snapshot, delete_snapshot)
from auth import get_current_user, is_pro


# ── Language helper ───────────────────────────────────────────────────────────

def _en() -> bool:
    """True when UI is in English-only mode."""
    return st.session_state.get("lang", "bilingual") == "english"


def _t(zh: str, en: str) -> str:
    """Return English text or bilingual text depending on lang setting."""
    return en if _en() else f"{zh} {en}" if zh != en else zh


# ── Keys that define a complete project state ─────────────────────────────────
# Mirrors DEFAULT_PARAMS in app.py
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
    # Project timeline
    "bess_lead_months", "pv_lead_months",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _default_name() -> str:
    """Generate default project name from current session state."""
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
                json.dumps(val)
                params[key] = val
            except (TypeError, ValueError):
                params[key] = str(val)
    return params


def get_results_summary() -> dict:
    """Extract lightweight results summary for project list display."""
    res = st.session_state.get("results")
    if not res:
        return {}
    return {
        "npv":     round(res.get("npv", 0), 0),
        "irr":     round(res.get("irr", 0), 2),
        "payback": round(res.get("simple_payback", 0), 2),
    }


def restore_snapshot(params: dict,
                     snap_id: str | None = None,
                     snap_name: str | None = None) -> None:
    """Load all project params back into session_state.
    Also sets active-project context so the UI knows which project is loaded.
    """
    for key, val in params.items():
        st.session_state[key] = val
    for k in ("results", "fin_df", "hourly_df"):
        st.session_state[k] = None
    # ── Sync divergent widget-state keys so number_inputs reflect restored values.
    # The lat/lon inputs use key="_lat_in"/"_lon_in" (not "lat"/"lon"), so Streamlit
    # would otherwise display the stale widget value and then overwrite the restored
    # coordinates in the next render cycle.
    if "lat" in params:
        st.session_state["_lat_in"] = params["lat"]
    if "lon" in params:
        st.session_state["_lon_in"] = params["lon"]
    # ── Active-project tracking ──────────────────────────────
    st.session_state["_active_snap_id"]     = snap_id
    st.session_state["_active_snap_name"]   = snap_name
    st.session_state["_snap_loaded_params"] = dict(params)   # baseline for dirty-check


def _is_dirty() -> bool:
    """True if any tracked param differs from the last-loaded snapshot baseline."""
    loaded = st.session_state.get("_snap_loaded_params")
    if not loaded:
        return False
    current = get_params_to_save()
    return any(current.get(k) != v for k, v in loaded.items())


def get_active_project() -> tuple:
    """Return (snap_id, snap_name, is_dirty) for the currently loaded project.
    Returns (None, None, False) when no project is loaded.
    """
    snap_id   = st.session_state.get("_active_snap_id")
    snap_name = st.session_state.get("_active_snap_name")
    if not snap_id:
        return None, None, False
    return snap_id, snap_name, _is_dirty()


# ════════════════════════════════════════════════════════════════════════════
# Main panel
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

    # ── Header: title + collapse toggle + save button ──
    h1, h2, h3 = st.columns([5, 2, 2])
    with h1:
        title = "📂 Projects" if _en() else "📂 项目 Projects"
        st.markdown(
            f"**{title}** `{count}`**/**`{limit_str}` {_tier_icon}",
            unsafe_allow_html=True,
        )
    with h2:
        _expanded = st.session_state.get("_snap_expanded", True)
        if _en():
            toggle_lbl = "▲ Hide" if _expanded else "▼ Show"
        else:
            toggle_lbl = "▲ 收起" if _expanded else "▼ 展开"
        if st.button(toggle_lbl, key="snap_toggle_btn", use_container_width=True):
            st.session_state["_snap_expanded"] = not _expanded
            st.rerun()
    with h3:
        save_lbl = "💾 Save" if _en() else "💾 保存 Save"
        if st.button(save_lbl, use_container_width=True, key="snap_save_btn",
                     type="primary"):
            if count >= limit:
                _show_limit_msg(tier, limit)
            else:
                st.session_state["_snap_save_open"]    = True
                st.session_state["_snap_default_name"] = _default_name()

    # ── Active-project context bar ──────────────────────────────────────────
    _aid, _aname, _dirty = get_active_project()
    if _aname:
        if _dirty:
            _bar_bg  = "#2a1a00"
            _bar_bd  = "#e67e22"
            _bar_ico = "✏️"
            _bar_lbl = "Unsaved changes" if _en() else "有未保存的修改"
        else:
            _bar_bg  = "#0a1f12"
            _bar_bd  = "#27ae60"
            _bar_ico = "✅"
            _bar_lbl = "Synced" if _en() else "已同步"
        st.markdown(
            f'<div style="background:{_bar_bg};border-left:3px solid {_bar_bd};'
            f'padding:3px 8px;border-radius:4px;font-size:0.76em;'
            f'margin:2px 0 3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'{_bar_ico} <b>{_aname}</b>&nbsp;·&nbsp;{_bar_lbl}</div>',
            unsafe_allow_html=True,
        )

    # ── Save dialog ──
    if st.session_state.get("_snap_save_open"):
        _render_save_dialog(user_id)

    # ── Collapsible project list ──
    if not st.session_state.get("_snap_expanded", True):
        return

    if not snapshots:
        empty_msg = ("No projects yet" if _en()
                     else "暂无项目 / No projects yet")
        st.markdown(
            f"<div style='color:#888;font-size:0.82em;text-align:center;"
            f"padding:8px 0'>{empty_msg}</div>",
            unsafe_allow_html=True,
        )
        return

    for snap in snapshots:
        _render_snapshot_item(snap)


# ── Save dialog ───────────────────────────────────────────────────────────────

def _render_save_dialog(user_id: str) -> None:
    default = st.session_state.get("_snap_default_name", _default_name())
    label   = "Project Name" if _en() else "项目名称 Project Name"
    ph      = "e.g. Site A · 100kWp+200kWh"
    name = st.text_input(label, value=default, key="snap_name_input",
                         placeholder=ph)
    ok_col, cancel_col = st.columns(2)
    with ok_col:
        ok_lbl = "✅ Save" if _en() else "✅ 保存 Save"
        if st.button(ok_lbl, type="primary", use_container_width=True,
                     key="snap_dialog_ok"):
            final       = name.strip() or default
            _saved_params = get_params_to_save()
            result = save_snapshot(
                user_id=user_id,
                name=final,
                default_name=_default_name(),
                params=_saved_params,
                results=get_results_summary(),
            )
            if result:
                # New project becomes the active project (clean state)
                st.session_state["_active_snap_id"]     = result.get("id")
                st.session_state["_active_snap_name"]   = final
                st.session_state["_snap_loaded_params"] = dict(_saved_params)
                msg = f"Saved: {final}" if _en() else f"✅ 已保存: {final}"
                st.toast(f"✅ {msg}" if _en() else msg)
            _close_dialog()
    with cancel_col:
        cancel_lbl = "✖ Cancel" if _en() else "✖ 取消 Cancel"
        if st.button(cancel_lbl, use_container_width=True,
                     key="snap_dialog_cancel"):
            _close_dialog()


def _close_dialog():
    for k in ("_snap_save_open", "_snap_default_name", "snap_name_input"):
        st.session_state.pop(k, None)
    st.rerun()


# ── Single project item ───────────────────────────────────────────────────────

def _render_snapshot_item(snap: dict) -> None:
    snap_id = snap["id"]
    name    = snap["name"]
    default = snap.get("default_name") or name
    pinned  = snap.get("is_pinned", False)
    results = snap.get("results_json") or {}

    try:
        dt = datetime.fromisoformat(snap["updated_at"].replace("Z", "+00:00"))
        ts = dt.strftime("%m-%d %H:%M")
    except Exception:
        ts = ""

    npv   = results.get("npv", 0)
    irr   = results.get("irr", 0)
    badge = (f"NPV {npv/1e6:+.1f}M · IRR {irr:.1f}%"
             if npv else ("Not run" if _en() else "未运算"))

    pin_icon  = "★ " if pinned else ""
    is_active = (snap_id == st.session_state.get("_active_snap_id"))

    # Active-project highlight border
    if is_active:
        _dirty = _is_dirty()
        _hi_color = "#e67e22" if _dirty else "#27ae60"
        st.markdown(
            f'<div style="border-left:3px solid {_hi_color};'
            f'padding-left:4px;margin:0 0 -4px">',
            unsafe_allow_html=True,
        )

    # ── Load button + ⋮ menu ──
    load_col, menu_col = st.columns([11, 1])

    with load_col:
        _active_prefix = "▶ " if is_active else ""
        load_tip = f"Load · {default}" if _en() else f"点击加载 / Load · {default}"
        if st.button(
            f"{_active_prefix}{pin_icon}{name}  ·  {badge}  ·  {ts}",
            key=f"snap_load_{snap_id}",
            use_container_width=True,
            help=load_tip,
        ):
            full = get_snapshot_full(snap_id)
            if full and full.get("params_json"):
                restore_snapshot(full["params_json"],
                                 snap_id=snap_id, snap_name=name)
                msg = f"Loaded: {name}" if _en() else f"已加载: {name}"
                st.toast(f"✅ {msg}")
                st.rerun()
            else:
                err = "Failed to load project" if _en() else "项目读取失败 / Failed to load"
                st.error(err)

    if is_active:
        st.markdown("</div>", unsafe_allow_html=True)

    with menu_col:
        with st.popover("⋮", use_container_width=True):
            st.markdown(f"**{name}**")
            st.divider()

            # Pin / Unpin
            if pinned:
                pin_lbl = "📍 Unpin" if _en() else "📍 取消置顶 Unpin"
            else:
                pin_lbl = "📌 Pin" if _en() else "📌 置顶 Pin"
            if st.button(pin_lbl, key=f"pm_pin_{snap_id}",
                         use_container_width=True):
                update_snapshot(snap_id, is_pinned=not pinned)
                st.rerun()

            # Rename
            ren_lbl = "✏️ Rename" if _en() else "✏️ 重命名 Rename"
            if st.button(ren_lbl, key=f"pm_ren_{snap_id}",
                         use_container_width=True):
                st.session_state[f"_ren_{snap_id}"] = True
                st.rerun()

            # Update config
            upd_lbl = "♻️ Update Config" if _en() else "♻️ 更新配置 Update"
            upd_tip = ("Overwrite with current params"
                       if _en() else "用当前参数覆盖此项目")
            if st.button(upd_lbl, key=f"pm_upd_{snap_id}",
                         use_container_width=True, help=upd_tip):
                _cur_params = get_params_to_save()
                update_snapshot(snap_id,
                                params_json=_cur_params,
                                results_json=get_results_summary(),
                                default_name=_default_name())
                # Reset dirty baseline so indicator turns green again
                st.session_state["_active_snap_id"]     = snap_id
                st.session_state["_active_snap_name"]   = name
                st.session_state["_snap_loaded_params"] = dict(_cur_params)
                msg = f"Updated: {name}" if _en() else f"已更新: {name}"
                st.toast(f"✅ {msg}")
                st.rerun()

            st.divider()

            # Delete
            del_lbl = "🗑️ Delete" if _en() else "🗑️ 删除 Delete"
            if st.button(del_lbl, key=f"pm_del_{snap_id}",
                         use_container_width=True, type="primary"):
                st.session_state[f"_del_{snap_id}"] = True
                st.rerun()

    # ── Inline rename ──
    if st.session_state.get(f"_ren_{snap_id}"):
        ren_label = "New name" if _en() else "新名称 New name"
        new_name  = st.text_input(ren_label, value=name,
                                   key=f"ren_inp_{snap_id}")
        rn1, rn2  = st.columns(2)
        with rn1:
            ok_l = "✅ Confirm" if _en() else "✅ 确认 Confirm"
            if st.button(ok_l, key=f"ren_ok_{snap_id}",
                         use_container_width=True, type="primary"):
                if new_name.strip():
                    update_snapshot(snap_id, name=new_name.strip())
                st.session_state.pop(f"_ren_{snap_id}", None)
                st.rerun()
        with rn2:
            ca_l = "✖ Cancel" if _en() else "✖ 取消 Cancel"
            if st.button(ca_l, key=f"ren_cancel_{snap_id}",
                         use_container_width=True):
                st.session_state.pop(f"_ren_{snap_id}", None)
                st.rerun()

    # ── Inline delete confirm ──
    if st.session_state.get(f"_del_{snap_id}"):
        warn_msg = (f"Delete '{name}'?" if _en()
                    else f"确认删除 '{name}'？")
        st.warning(warn_msg)
        d1, d2 = st.columns(2)
        with d1:
            confirm_l = "✅ Delete" if _en() else "✅ 确认删除"
            if st.button(confirm_l, key=f"del_ok_{snap_id}",
                         type="primary", use_container_width=True):
                delete_snapshot(snap_id)
                st.session_state.pop(f"_del_{snap_id}", None)
                msg = "Deleted" if _en() else "已删除"
                st.toast(f"🗑️ {msg}")
                st.rerun()
        with d2:
            cancel_l = "✖ Cancel" if _en() else "✖ 取消 Cancel"
            if st.button(cancel_l, key=f"del_cancel_{snap_id}",
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
        if _en():
            st.error(
                f"Free tier limit ({limit} projects) reached. "
                f"Contact admin to upgrade to 🔵 Pro (50 projects)."
            )
        else:
            st.error(
                f"已达免费版项目上限（{limit} 个）。"
                f"请联系管理员升级为 🔵 Pro 版（50个项目）。\n\n"
                f"Free tier limit ({limit} projects) reached. "
                f"Contact admin to upgrade to 🔵 Pro."
            )
    else:
        msg = (f"Project limit ({limit}) reached"
               if _en() else f"已达项目上限 {limit} 个 / Project limit ({limit}) reached")
        st.error(msg)
