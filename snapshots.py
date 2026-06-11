"""
snapshots.py — Project (Snapshot) Management Panel
BTM PV+BESS Financial Modelling System
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st

from db import (get_snapshots, get_snapshot_full, save_snapshot,
                update_snapshot, delete_snapshot)
from auth import get_current_user, is_pro


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
    _lcoe = res.get("lcoe", {})
    return {
        "npv":              round(res.get("npv", 0), 0),
        "irr":              round(res.get("irr", 0), 2),
        "payback":          round(res.get("payback", 0) or 0, 2),
        "lcoe_zar_kwh":     _lcoe.get("lcoe_zar_kwh", 0),
        "total_avoided_mwh": _lcoe.get("total_avoided_mwh", 0),
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
        st.markdown(
            f"**📂 Projects** `{count}`**/**`{limit_str}` {_tier_icon}",
            unsafe_allow_html=True,
        )
    with h2:
        _expanded = st.session_state.get("_snap_expanded", True)
        toggle_lbl = "▲ Hide" if _expanded else "▼ Show"
        if st.button(toggle_lbl, key="snap_toggle_btn", use_container_width=True):
            st.session_state["_snap_expanded"] = not _expanded
            st.rerun()
    with h3:
        if st.button("💾 Save", use_container_width=True, key="snap_save_btn",
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
            _bar_lbl = "Unsaved changes"
        else:
            _bar_bg  = "#0a1f12"
            _bar_bd  = "#27ae60"
            _bar_ico = "✅"
            _bar_lbl = "Synced"
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
        st.markdown(
            "<div style='color:#888;font-size:0.82em;text-align:center;"
            "padding:8px 0'>No projects yet</div>",
            unsafe_allow_html=True,
        )
        return

    for snap in snapshots:
        _render_snapshot_item(snap)


# ── Save dialog ───────────────────────────────────────────────────────────────

_NEW_FOLDER_SENTINEL = "＋ New folder…"


def _get_existing_folders(user_id: str) -> list[str]:
    """Return sorted list of existing folder names (client_names), General last."""
    snaps = get_snapshots(user_id)
    names = sorted(set(
        s["client_name"].strip()
        for s in snaps
        if s.get("client_name", "").strip()
    ))
    # Always include General; put it last
    if "General" in names:
        names.remove("General")
    return names + ["General"]


def _render_save_dialog(user_id: str) -> None:
    default_name = st.session_state.get("_snap_default_name", _default_name())

    # ── Folder selector ──────────────────────────────────────────────────────
    existing = _get_existing_folders(user_id)
    folder_options = existing + [_NEW_FOLDER_SENTINEL]

    # Pre-select last-used folder
    _prev = st.session_state.get("_snap_last_folder", "General")
    _idx  = folder_options.index(_prev) if _prev in folder_options else folder_options.index("General")

    _fc, _nc = st.columns([2, 3])
    with _fc:
        selected = st.selectbox(
            "Folder",
            options=folder_options,
            index=_idx,
            key="snap_folder_select",
        )
    with _nc:
        name = st.text_input(
            "Project Name", value=default_name,
            key="snap_name_input",
            placeholder="e.g. Site A · 100kWp+200kWh",
        )

    # ── New folder text input ─────────────────────────────────────────────────
    new_folder_name = ""
    _folder_dup_err = False
    if selected == _NEW_FOLDER_SENTINEL:
        new_folder_name = st.text_input(
            "New folder name",
            key="snap_new_folder_input",
            placeholder="e.g. Impala Projects",
            label_visibility="collapsed",
        )
        # Duplicate check (case-insensitive)
        if new_folder_name.strip():
            _existing_lc = [f.lower() for f in existing]
            if new_folder_name.strip().lower() in _existing_lc:
                st.error(f"⚠️ Folder **{new_folder_name.strip()}** already exists — pick a different name.")
                _folder_dup_err = True
        else:
            st.caption("Enter new folder name above")

    # Resolve final client/folder value
    if selected == _NEW_FOLDER_SENTINEL:
        final_client = new_folder_name.strip()
    elif selected == "General":
        final_client = ""          # store as empty → displays as General
    else:
        final_client = selected

    ok_col, cancel_col = st.columns(2)
    with ok_col:
        if st.button("✅ Save", type="primary", use_container_width=True,
                     key="snap_dialog_ok",
                     disabled=_folder_dup_err):
            final_name    = name.strip() or default_name
            _saved_params = get_params_to_save()
            result = save_snapshot(
                user_id=user_id,
                name=final_name,
                default_name=_default_name(),
                params=_saved_params,
                results=get_results_summary(),
                client_name=final_client,
            )
            if result:
                st.session_state["_active_snap_id"]     = result.get("id")
                st.session_state["_active_snap_name"]   = final_name
                st.session_state["_snap_loaded_params"] = dict(_saved_params)
                # Remember folder for next save
                st.session_state["_snap_last_folder"] = selected if selected != _NEW_FOLDER_SENTINEL else new_folder_name.strip()
                st.toast(f"✅ Saved: {final_name}")
            _close_dialog()
    with cancel_col:
        if st.button("✖ Cancel", use_container_width=True,
                     key="snap_dialog_cancel"):
            _close_dialog()


def _close_dialog():
    for k in ("_snap_save_open", "_snap_default_name", "_snap_client_name",
              "snap_name_input", "snap_folder_select", "snap_new_folder_input"):
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
             if npv else "Not run")

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
        if st.button(
            f"{_active_prefix}{pin_icon}{name}  ·  {badge}  ·  {ts}",
            key=f"snap_load_{snap_id}",
            use_container_width=True,
            help=f"Load · {default}",
        ):
            full = get_snapshot_full(snap_id)
            if full and full.get("params_json"):
                restore_snapshot(full["params_json"],
                                 snap_id=snap_id, snap_name=name)
                st.toast(f"✅ Loaded: {name}")
                st.rerun()
            else:
                st.error("Failed to load project")

    if is_active:
        st.markdown("</div>", unsafe_allow_html=True)

    with menu_col:
        with st.popover("⋮", use_container_width=True):
            st.markdown(f"**{name}**")
            st.divider()

            # Pin / Unpin
            pin_lbl = "📍 Unpin" if pinned else "📌 Pin"
            if st.button(pin_lbl, key=f"pm_pin_{snap_id}",
                         use_container_width=True):
                update_snapshot(snap_id, is_pinned=not pinned)
                st.rerun()

            # Rename
            if st.button("✏️ Rename", key=f"pm_ren_{snap_id}",
                         use_container_width=True):
                st.session_state[f"_ren_{snap_id}"] = True
                st.rerun()

            # Update config
            if st.button("♻️ Update Config", key=f"pm_upd_{snap_id}",
                         use_container_width=True,
                         help="Overwrite with current params"):
                _cur_params = get_params_to_save()
                update_snapshot(snap_id,
                                params_json=_cur_params,
                                results_json=get_results_summary(),
                                default_name=_default_name())
                # Reset dirty baseline so indicator turns green again
                st.session_state["_active_snap_id"]     = snap_id
                st.session_state["_active_snap_name"]   = name
                st.session_state["_snap_loaded_params"] = dict(_cur_params)
                st.toast(f"✅ Updated: {name}")
                st.rerun()

            st.divider()

            # Delete
            if st.button("🗑️ Delete", key=f"pm_del_{snap_id}",
                         use_container_width=True, type="primary"):
                st.session_state[f"_del_{snap_id}"] = True
                st.rerun()

    # ── Inline rename ──
    if st.session_state.get(f"_ren_{snap_id}"):
        new_name  = st.text_input("New name", value=name,
                                   key=f"ren_inp_{snap_id}")
        rn1, rn2  = st.columns(2)
        with rn1:
            if st.button("✅ Confirm", key=f"ren_ok_{snap_id}",
                         use_container_width=True, type="primary"):
                if new_name.strip():
                    update_snapshot(snap_id, name=new_name.strip())
                st.session_state.pop(f"_ren_{snap_id}", None)
                st.rerun()
        with rn2:
            if st.button("✖ Cancel", key=f"ren_cancel_{snap_id}",
                         use_container_width=True):
                st.session_state.pop(f"_ren_{snap_id}", None)
                st.rerun()

    # ── Inline delete confirm ──
    if st.session_state.get(f"_del_{snap_id}"):
        st.warning(f"Delete '{name}'?")
        d1, d2 = st.columns(2)
        with d1:
            if st.button("✅ Delete", key=f"del_ok_{snap_id}",
                         type="primary", use_container_width=True):
                delete_snapshot(snap_id)
                st.session_state.pop(f"_del_{snap_id}", None)
                st.toast("🗑️ Deleted")
                st.rerun()
        with d2:
            if st.button("✖ Cancel", key=f"del_cancel_{snap_id}",
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
            f"Free tier limit ({limit} projects) reached. "
            f"Contact admin to upgrade to 🔵 Pro (50 projects)."
        )
    else:
        st.error(f"Project limit ({limit}) reached")


# ════════════════════════════════════════════════════════════════════════════
# New compact project bar  (replaces render_snapshot_panel in app.py)
# ════════════════════════════════════════════════════════════════════════════

_CARD_CSS = """
<style>
/* ═══════════════════════════════════════════════════════════════
   ALL Streamlit Popovers → dark theme
   (Selectors are global so they reach React portals)
   ═══════════════════════════════════════════════════════════════ */

/* ── Dark background for every popover ─────────────────────── */
[data-testid="stPopoverBody"] {
    background:    #161616 !important;
    border:        1px solid #2a2a2a !important;
    border-radius: 10px !important;
    padding:       0 !important;
    overflow:      hidden !important;
}
[data-testid="stPopoverBody"] > div {
    padding: 6px 0 10px !important;
}

/* ── Column layout ─────────────────────────────────────────── */
[data-testid="stPopoverBody"] div[data-testid="stHorizontalBlock"] {
    gap:          0 !important;
    padding:      0 6px !important;
    align-items:  center !important;
}
[data-testid="stPopoverBody"] div[data-testid="stColumn"] {
    padding:   1px 2px !important;
    min-width: 0 !important;
}

/* ── ALL secondary buttons → borderless text rows ──────────── */
[data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"] {
    background:      transparent !important;
    border:          none !important;
    box-shadow:      none !important;
    border-radius:   5px !important;
    padding:         3px 10px !important;
    margin:          0 !important;
    height:          32px !important;
    min-height:      32px !important;
    width:           100% !important;
    justify-content: flex-start !important;
    color:           #c9d1d9 !important;
    font-size:       0.84em !important;
    transition:      background 0.1s !important;
}
[data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"]:hover {
    background: rgba(255,255,255,0.07) !important;
    color:      #f0f6fc !important;
}
[data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"] p,
[data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"] > div {
    text-align:      left !important;
    overflow:        hidden !important;
    text-overflow:   ellipsis !important;
    white-space:     nowrap !important;
    justify-content: flex-start !important;
}

/* ── Active project (primary + disabled) → green accent ─────── */
[data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"],
[data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"]:disabled {
    background:      rgba(0,229,160,0.09) !important;
    border:          none !important;
    border-left:     3px solid #00E5A0 !important;
    border-radius:   0 5px 5px 0 !important;
    box-shadow:      none !important;
    color:           #00E5A0 !important;
    font-weight:     600 !important;
    padding-left:    8px !important;
    justify-content: flex-start !important;
    opacity:         1 !important;
    height:          32px !important;
    min-height:      32px !important;
    width:           100% !important;
}
[data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"] p,
[data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"] > div,
[data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"]:disabled p,
[data-testid="stPopoverBody"] [data-testid="stBaseButton-primary"]:disabled > div {
    text-align:      left !important;
    overflow:        hidden !important;
    text-overflow:   ellipsis !important;
    white-space:     nowrap !important;
    color:           #00E5A0 !important;
    justify-content: flex-start !important;
}

/* ── ⋮ button (project picker only, last column) ───────────── */
div[data-testid="stPopoverBody"]:has(.proj-picker-marker)
    div[data-testid="stColumn"]:last-child button {
    width:           26px !important;
    min-width:       26px !important;
    max-width:       26px !important;
    height:          26px !important;
    min-height:      26px !important;
    padding:         0 !important;
    justify-content: center !important;
    color:           #3d4451 !important;
    border-radius:   4px !important;
    font-size:       1em !important;
}
div[data-testid="stPopoverBody"]:has(.proj-picker-marker)
    div[data-testid="stColumn"]:last-child button:hover {
    background: rgba(255,255,255,0.10) !important;
    color:      #8b949e !important;
}

/* ── Folder expanders ──────────────────────────────────────── */
[data-testid="stPopoverBody"] [data-testid="stExpander"] {
    background: transparent !important;
    border:     none !important;
    margin:     0 !important;
    padding:    0 !important;
}
[data-testid="stPopoverBody"] [data-testid="stExpander"] summary,
[data-testid="stPopoverBody"] details[data-testid="stExpander"] > summary {
    background:     transparent !important;
    border:         none !important;
    color:          #6e7681 !important;
    font-size:      0.72em !important;
    font-weight:    700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding:        10px 14px 4px !important;
}
[data-testid="stPopoverBody"] [data-testid="stExpander"] summary:hover {
    color:      #9ca3af !important;
    background: rgba(255,255,255,0.03) !important;
}
[data-testid="stPopoverBody"] [data-testid="stExpander"] summary svg {
    color:  #484f58 !important;
    width:  12px !important;
    height: 12px !important;
}
[data-testid="stPopoverBody"] [data-testid="stExpanderDetails"] {
    padding:    1px 0 4px !important;
    background: transparent !important;
    border:     none !important;
}

/* ── Caption text & dividers ───────────────────────────────── */
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] p {
    color:     #6e7681 !important;
    font-size: 0.80em !important;
}
[data-testid="stPopoverBody"] div[data-testid="stMarkdownContainer"] p {
    color:     #e0e6ed !important;  /* readable white for menu headings */
}
[data-testid="stPopoverBody"] div[data-testid="stMarkdownContainer"] p em,
[data-testid="stPopoverBody"] div[data-testid="stMarkdownContainer"] p small {
    color:     #8b949e !important;
    font-size: 0.82em !important;
}
[data-testid="stPopoverBody"] hr {
    border-color: #21262d !important;
    margin:       3px 10px !important;
}

/* ── Drag-and-drop ─────────────────────────────────────────── */
/* Row being dragged */
[data-testid="stHorizontalBlock"].dnd-dragging {
    opacity: 0.4 !important;
    cursor:  grabbing !important;
}
/* Folder expander highlighted as drop target */
[data-testid="stExpander"].dnd-drop-over summary {
    background: rgba(0,229,160,0.12) !important;
    outline:    2px dashed #00E5A0 !important;
    border-radius: 6px !important;
}
/* Drag-handle cursor on project rows */
[data-drag-row] {
    cursor: grab !important;
}
[data-drag-row]:active {
    cursor: grabbing !important;
}

/* ── Move-to folder picker: sub-folder buttons ─────────────── */
[data-testid="stPopoverBody"] [data-testid="stBaseButton-secondary"].move-to-current {
    color:          #00E5A0 !important;
    pointer-events: none !important;
}

/* ── DnD bridge input: hide completely but keep functional ──── */
input[placeholder="__dnd__"] {
    position:       fixed !important;
    left:           -9999px !important;
    top:            -9999px !important;
    width:          1px !important;
    height:         1px !important;
    opacity:        0 !important;
    pointer-events: none !important;
}
[data-testid="stTextInputRootElement"]:has(input[placeholder="__dnd__"]) {
    display: none !important;
}
</style>
"""


_DND_JS = """
<script>
(function() {
    var PARENT = (window.parent && window.parent.document) ? window.parent.document : document;
    var _dragging = null;

    function setupAll() {
        // ── Drag sources: project rows ──────────────────────────
        PARENT.querySelectorAll('dfn[data-drag-snap]').forEach(function(dfn) {
            if (dfn._dndReady) return;
            dfn._dndReady = true;
            var snapId = dfn.getAttribute('data-drag-snap');
            var mc  = dfn.parentElement;           // stMarkdownContainer
            var row = mc && mc.nextElementSibling; // stHorizontalBlock
            if (!row) return;
            row.setAttribute('draggable', 'true');
            row.style.cursor = 'grab';
            row.addEventListener('dragstart', function(e) {
                _dragging = snapId;
                e.dataTransfer.setData('text/plain', snapId);
                e.dataTransfer.effectAllowed = 'move';
                row.style.opacity = '0.4';
            });
            row.addEventListener('dragend', function() {
                _dragging = null;
                row.style.opacity = '';
                // Remove all drop highlights
                PARENT.querySelectorAll('[data-testid="stExpander"]').forEach(function(ex) {
                    ex.querySelector('summary') && (ex.querySelector('summary').style.outline = '');
                    ex.style.background = '';
                });
            });
        });

        // ── Drop targets: folder expanders ──────────────────────
        PARENT.querySelectorAll('dfn[data-drag-folder]').forEach(function(dfn) {
            if (dfn._dndReady) return;
            dfn._dndReady = true;
            var folder  = dfn.getAttribute('data-drag-folder');
            var mc      = dfn.parentElement;
            var expander = mc && mc.nextElementSibling;
            if (!expander) return;
            expander.addEventListener('dragover', function(e) {
                if (!_dragging) return;
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                var sum = expander.querySelector('summary');
                if (sum) sum.style.outline = '2px dashed #00E5A0';
            });
            expander.addEventListener('dragleave', function() {
                var sum = expander.querySelector('summary');
                if (sum) sum.style.outline = '';
            });
            expander.addEventListener('drop', function(e) {
                e.preventDefault();
                var sum = expander.querySelector('summary');
                if (sum) sum.style.outline = '';
                var snapId = e.dataTransfer.getData('text/plain') || _dragging;
                if (snapId) triggerMove(snapId, folder);
            });
        });
    }

    function triggerMove(snapId, folder) {
        var inputs = PARENT.querySelectorAll('input[placeholder="__dnd__"]');
        if (!inputs.length) { return; }
        var input = inputs[0];
        try {
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(input, snapId + '|' + folder);
        } catch(ex) {
            input.value = snapId + '|' + folder;
        }
        input.dispatchEvent(new Event('input', {bubbles: true}));
    }

    // Multiple retries to handle Streamlit's async rendering
    setTimeout(setupAll, 250);
    setTimeout(setupAll, 800);
    setTimeout(setupAll, 2000);
})();
</script>
"""


def render_project_bar() -> None:
    """
    Full-width project picker bar — sits ABOVE the main col split in app.py.

    Layout (1 line):
        [📁 Projects ▾ (popover)]  ·  [active project status]  ·  [💾 Save as New Project]

    The popover shows projects grouped by client in collapsible folders.
    Clicking a project name loads it; ⋮ menu offers Pin/Rename/Move to…/Update/Delete.
    Supports drag-and-drop between folders.
    """
    import streamlit.components.v1 as components
    from collections import defaultdict

    user = get_current_user()
    if not user:
        return

    st.markdown(_CARD_CSS, unsafe_allow_html=True)

    user_id   = user["id"]
    limit     = user.get("snapshot_limit", 3)
    tier      = user.get("tier", "free")
    limit_str = "∞" if limit >= 999999 else str(limit)

    snapshots = get_snapshots(user_id)
    count     = len(snapshots)

    # ── DnD bridge: hidden text input for JS → Python communication ───────────
    # Rendered OUTSIDE the popover so it persists in the DOM.
    # JS writes "snap_id|folder_name" to this input via React native setter.
    if "_dnd_action" not in st.session_state:
        st.session_state["_dnd_action"] = ""
    st.text_input("", key="_dnd_action", placeholder="__dnd__",
                  label_visibility="collapsed")

    # ── Process any pending drag-drop move ────────────────────────────────────
    _dnd = st.session_state.get("_dnd_action", "")
    if _dnd and "|" in _dnd:
        _dnd_sid, _dnd_fol = _dnd.split("|", 1)
        st.session_state["_dnd_action"] = ""   # clear BEFORE rerun
        try:
            update_snapshot(_dnd_sid, client_name=("" if _dnd_fol == "General" else _dnd_fol))
            st.toast(f"📂 Moved to {_dnd_fol or 'General'}")
        except Exception as _e:
            st.error(f"Move failed: {_e}")
        st.rerun()

    # ── Save dialog (full-width, shown inline when triggered) ──────────────
    if st.session_state.get("_snap_save_open"):
        _render_save_dialog(user_id)
        return

    # ── Top bar: [📁 Projects ▾]  [status]  [💾 Save] ──────────────────────
    _bc1, _bc2, _bc3 = st.columns([2, 8, 2])

    with _bc1:
        _btn_lbl = f"📁 Projects  {count}/{limit_str} ▾"
        with st.popover(_btn_lbl, use_container_width=True):
            # Width-forcing marker (forces popover ≥440px) + CSS scope anchor
            st.markdown(
                '<div class="proj-picker-marker" '
                'style="min-width:440px;height:0;line-height:0;font-size:0;'
                'overflow:hidden;margin:0;padding:0"></div>',
                unsafe_allow_html=True,
            )
            if not snapshots:
                st.markdown(
                    "<div style='color:#667;font-size:0.85em;padding:6px 2px'>"
                    "No projects yet — click 💾 Save to create one</div>",
                    unsafe_allow_html=True,
                )
                client_groups = {}
            else:
                # ── Group by client_name ──────────────────────────────────
                active_id     = st.session_state.get("_active_snap_id")
                client_groups: dict[str, list] = defaultdict(list)
                for _s in snapshots:
                    _client = (_s.get("client_name") or "").strip() or "General"
                    client_groups[_client].append(_s)

                # Sort: named clients alphabetically first, "General" last
                def _sort_key(c):
                    return (1, c.lower()) if c == "General" else (0, c.lower())
                sorted_clients = sorted(client_groups.keys(), key=_sort_key)

                for _client in sorted_clients:
                    _grp = client_groups[_client]
                    _n   = len(_grp)
                    # Auto-expand the folder that contains the active project
                    _expanded = any(s["id"] == active_id for s in _grp)
                    _folder_lbl = f"📂 {_client}  ({_n})"
                    # ── Drag-drop TARGET marker (JS attaches drop listener to next sibling) ──
                    st.markdown(
                        f'<dfn data-drag-folder="{_client}" style="display:none"></dfn>',
                        unsafe_allow_html=True,
                    )
                    with st.expander(_folder_lbl, expanded=_expanded):
                        for _snap in _grp:
                            _render_project_card(_snap, user_id=user_id)

                # ── Drag-and-drop JS component (same-origin iframe) ───────
                components.html(_DND_JS, height=0, scrolling=False)

            # ── New Folder — always at bottom of folder list ──────────────
            st.markdown(
                "<hr style='border-color:#21262d;margin:6px 0 4px'>",
                unsafe_allow_html=True,
            )
            if st.session_state.get("_pb_new_folder_mode"):
                _nf_inp = st.text_input(
                    "Folder name",
                    key="_pb_nf_inp",
                    placeholder="Client or group name…",
                    label_visibility="collapsed",
                )
                # Duplicate check against existing folders
                _existing_fol = list(client_groups.keys())
                _nf_dup = bool(
                    _nf_inp.strip()
                    and _nf_inp.strip().lower() in [x.lower() for x in _existing_fol]
                )
                if _nf_dup:
                    st.caption(f"⚠️  **{_nf_inp.strip()}** already exists")
                _nfa, _nfb = st.columns([3, 1])
                with _nfa:
                    if st.button(
                        "✅ Create Folder",
                        key="_pb_nf_ok",
                        use_container_width=True,
                        type="primary",
                        disabled=(_nf_dup or not _nf_inp.strip()),
                        help="Create folder and open Save dialog",
                    ):
                        _fn = _nf_inp.strip()
                        # Pre-populate the Save dialog with this new folder
                        st.session_state["_snap_save_open"]       = True
                        st.session_state["_snap_default_name"]    = _default_name()
                        st.session_state["snap_folder_select"]    = _NEW_FOLDER_SENTINEL
                        st.session_state["snap_new_folder_input"] = _fn
                        st.session_state.pop("_pb_new_folder_mode", None)
                        st.rerun()
                with _nfb:
                    if st.button("✖", key="_pb_nf_cx", use_container_width=True):
                        st.session_state.pop("_pb_new_folder_mode", None)
                        st.rerun()
            else:
                if st.button(
                    "📁  ＋  New Folder",
                    key="_pb_new_folder_btn",
                    use_container_width=True,
                    help="Create a new client folder",
                ):
                    st.session_state["_pb_new_folder_mode"] = True
                    st.rerun()

    with _bc2:
        _aid, _aname, _dirty = get_active_project()
        if _aname:
            _clr  = "#e67e22" if _dirty else "#27ae60"
            _ico  = "✏️"     if _dirty else "✅"
            _hint = "Unsaved changes" if _dirty else "Synced"
            st.markdown(
                f'<div style="background:#0d1520;border-left:3px solid {_clr};'
                f'padding:5px 10px;border-radius:4px;font-size:0.8em;margin-top:3px;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                f'{_ico} <b>{_aname}</b> &nbsp;·&nbsp; {_hint}</div>',
                unsafe_allow_html=True,
            )

    with _bc3:
        _can_save = count < limit
        if st.button("💾 Save as New Project", key="snap_save_btn", type="primary",
                     use_container_width=True, disabled=not _can_save,
                     help="Save current parameters as a new project"):
            st.session_state["_snap_save_open"]    = True
            st.session_state["_snap_default_name"] = _default_name()
            st.rerun()
        if not _can_save:
            _show_limit_msg(tier, limit)


# ── Individual project card ───────────────────────────────────────────────────

def _render_project_card(snap: dict, user_id: str = "") -> None:
    """Clean text-row: [name/load button]  [⋮ menu] — no card borders."""
    snap_id    = snap["id"]
    name       = snap["name"]
    pinned     = snap.get("is_pinned", False)
    client_now = (snap.get("client_name") or "").strip() or "General"
    results    = snap.get("results_json") or {}

    # ── Drag-and-drop source marker (JS reads this to set draggable) ──────────
    st.markdown(
        f'<dfn data-drag-snap="{snap_id}" style="display:none"></dfn>',
        unsafe_allow_html=True,
    )

    try:
        dt = datetime.fromisoformat(snap["updated_at"].replace("Z", "+00:00"))
        ts = dt.strftime("%b %d")
    except Exception:
        ts = ""

    is_active = snap_id == st.session_state.get("_active_snap_id")
    _dirty    = _is_dirty() if is_active else False

    npv  = results.get("npv", 0)
    irr  = results.get("irr", 0)
    lcoe = results.get("lcoe_zar_kwh", 0)
    _lcoe_str = f" · LCOE R{lcoe:.2f}/kWh" if lcoe else ""
    _meta = f"NPV {npv/1e6:+.1f}M · IRR {irr:.1f}%{_lcoe_str}" if npv else ts

    _pin_icon = "★ " if pinned else ""
    _short    = (name[:34] + "…") if len(name) > 36 else name
    _btn_lbl  = f"{_pin_icon}{_short}"
    _tooltip  = f"{name}  ·  {_meta}" + ("  ·  ✏️ unsaved" if _dirty else "")

    # ── [name button]  [⋮] ─────────────────────────────────────────────────
    _nc, _mc = st.columns([14, 1], gap="small")

    with _nc:
        if st.button(
            _btn_lbl,
            key=f"pc_load_{snap_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
            disabled=is_active,
            help=_tooltip,
        ):
            _full = get_snapshot_full(snap_id)
            if _full and _full.get("params_json"):
                restore_snapshot(_full["params_json"], snap_id=snap_id, snap_name=name)
                st.toast(f"✅ Loaded: {name}")
                st.rerun()
            else:
                st.error("Failed to load project")

    with _mc:
        with st.popover("⋮", use_container_width=True):
            st.markdown(f"**{name}**")
            st.caption(f"📂 {client_now}  ·  {ts}")
            st.divider()

            # Pin / Unpin
            _pin_lbl = "📍 Unpin" if pinned else "📌 Pin"
            if st.button(_pin_lbl, key=f"pc_pin_{snap_id}", use_container_width=True):
                update_snapshot(snap_id, is_pinned=not pinned)
                st.rerun()

            # Rename
            if st.button("✏️ Rename", key=f"pc_ren_{snap_id}", use_container_width=True):
                st.session_state[f"_pc_ren_{snap_id}"] = True
                st.rerun()

            # Move to folder
            if st.button("📁 Move to…", key=f"pc_mv_{snap_id}", use_container_width=True):
                st.session_state[f"_pc_mv_{snap_id}"] = not st.session_state.get(f"_pc_mv_{snap_id}", False)
                st.rerun()

            # Update config
            if st.button("♻️ Update Config", key=f"pc_upd_{snap_id}", use_container_width=True,
                         help="Overwrite with current params"):
                _cur = get_params_to_save()
                update_snapshot(snap_id,
                                params_json  = _cur,
                                results_json = get_results_summary(),
                                default_name = _default_name())
                st.session_state["_active_snap_id"]     = snap_id
                st.session_state["_active_snap_name"]   = name
                st.session_state["_snap_loaded_params"] = dict(_cur)
                st.toast(f"✅ Updated: {name}")
                st.rerun()

            st.divider()

            # Delete
            if st.button("🗑️ Delete", key=f"pc_del_{snap_id}",
                         use_container_width=True):
                st.session_state[f"_pc_del_{snap_id}"] = True
                st.rerun()

    # ── Inline rename ───────────────────────────────────────────────────────
    if st.session_state.get(f"_pc_ren_{snap_id}"):
        _new = st.text_input(
            "New name",
            value=name, key=f"pc_ren_inp_{snap_id}",
            label_visibility="collapsed",
            placeholder=name,
        )
        _r1, _r2 = st.columns(2)
        with _r1:
            if st.button("✅ OK", key=f"pc_ren_ok_{snap_id}", use_container_width=True,
                         type="primary"):
                if _new.strip():
                    update_snapshot(snap_id, name=_new.strip())
                    if st.session_state.get("_active_snap_name") == name:
                        st.session_state["_active_snap_name"] = _new.strip()
                st.session_state.pop(f"_pc_ren_{snap_id}", None)
                st.rerun()
        with _r2:
            if st.button("✖", key=f"pc_ren_cx_{snap_id}", use_container_width=True):
                st.session_state.pop(f"_pc_ren_{snap_id}", None)
                st.rerun()

    # ── Inline "Move to…" folder picker ────────────────────────────────────
    if st.session_state.get(f"_pc_mv_{snap_id}"):
        _mv_folders = _get_existing_folders(user_id) if user_id else ["General"]
        st.caption("Move to folder:")
        for _f in _mv_folders:
            _is_cur = (_f == client_now)
            _f_slug = str(abs(hash(_f)) % 9999999)
            _icon   = "✓ " if _is_cur else "📂 "
            _f_btn  = st.button(
                f"{_icon}{_f}",
                key=f"pc_mv_f_{snap_id}_{_f_slug}",
                use_container_width=True,
                disabled=_is_cur,
            )
            if _f_btn and not _is_cur:
                update_snapshot(snap_id, client_name=("" if _f == "General" else _f))
                st.session_state.pop(f"_pc_mv_{snap_id}", None)
                st.toast(f"📂 Moved to {_f}")
                st.rerun()

        # ── New folder sub-option ─────────────────────────────
        if st.session_state.get(f"_pc_mv_new_{snap_id}"):
            _nf = st.text_input(
                "New folder", key=f"pc_mv_nf_{snap_id}",
                label_visibility="collapsed",
                placeholder="Folder name…",
            )
            # Duplicate guard
            _nf_dup = _nf.strip() and _nf.strip().lower() in [x.lower() for x in _mv_folders]
            if _nf_dup:
                st.error(f"⚠️ **{_nf.strip()}** already exists")
            _na, _nb = st.columns(2)
            with _na:
                if st.button("✅", key=f"pc_mv_nfok_{snap_id}",
                             use_container_width=True, type="primary",
                             disabled=(_nf_dup or not _nf.strip())):
                    update_snapshot(snap_id, client_name=_nf.strip())
                    st.session_state.pop(f"_pc_mv_{snap_id}", None)
                    st.session_state.pop(f"_pc_mv_new_{snap_id}", None)
                    st.toast(f"📂 Moved to {_nf.strip()}")
                    st.rerun()
            with _nb:
                if st.button("✖", key=f"pc_mv_nfcx_{snap_id}", use_container_width=True):
                    st.session_state.pop(f"_pc_mv_new_{snap_id}", None)
                    st.rerun()
        else:
            if st.button("＋ New folder", key=f"pc_mv_newfol_{snap_id}",
                         use_container_width=True):
                st.session_state[f"_pc_mv_new_{snap_id}"] = True
                st.rerun()

        if st.button("✖ Close", key=f"pc_mv_cx_{snap_id}", use_container_width=True):
            st.session_state.pop(f"_pc_mv_{snap_id}", None)
            st.session_state.pop(f"_pc_mv_new_{snap_id}", None)
            st.rerun()

    # ── Inline delete confirm ───────────────────────────────────────────────
    if st.session_state.get(f"_pc_del_{snap_id}"):
        st.warning(f"Delete '{name}'?")
        _d1, _d2 = st.columns(2)
        with _d1:
            if st.button("✅ Yes", key=f"pc_del_ok_{snap_id}", use_container_width=True,
                         type="primary"):
                delete_snapshot(snap_id)
                if st.session_state.get("_active_snap_id") == snap_id:
                    for _k in ("_active_snap_id", "_active_snap_name",
                               "_snap_loaded_params"):
                        st.session_state.pop(_k, None)
                st.session_state.pop(f"_pc_del_{snap_id}", None)
                st.toast(f"🗑️ Deleted: {name}")
                st.rerun()
        with _d2:
            if st.button("✖", key=f"pc_del_cx_{snap_id}", use_container_width=True):
                st.session_state.pop(f"_pc_del_{snap_id}", None)
                st.rerun()
