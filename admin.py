"""
admin.py — Admin Panel
BTM PV+BESS Financial Modelling System

Only rendered when is_admin() is True.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import secrets as _secrets
import string as _string

from db import (create_user, get_all_users, update_user_tier, set_user_active,
                get_audit_log, get_system_stats)
from auth import get_current_user

# ── Tier display config ───────────────────────────────────────────────────────
_TIER_CFG = {
    "free":  {"label": "🆓 Free",  "default_limit": 3,      "color": "#888"},
    "pro":   {"label": "🔵 Pro",   "default_limit": 50,     "color": "#4af"},
    "admin": {"label": "🔴 Admin", "default_limit": 999999, "color": "#f44"},
}


# ════════════════════════════════════════════════════════════════════════════
# Main entry point
# ════════════════════════════════════════════════════════════════════════════

def render_admin_panel() -> None:
    actor_id = get_current_user()["id"]

    st.markdown("## 🔴 Admin Panel")

    t_users, t_create, t_stats, t_log = st.tabs([
        "👥 Users",
        "➕ Create User",
        "📊 Stats",
        "📋 Audit Log",
    ])

    with t_users:
        _render_users(actor_id)

    with t_create:
        _render_create_user(actor_id)

    with t_stats:
        _render_stats()

    with t_log:
        _render_audit_log()


# ════════════════════════════════════════════════════════════════════════════
# Create User tab
# ════════════════════════════════════════════════════════════════════════════

_TIER_LIMITS = {"free": 3, "pro": 50, "admin": 999999}
_PW_CHARS    = _string.ascii_letters + _string.digits + "!@#$%"


def _gen_password(length: int = 12) -> str:
    return "".join(_secrets.choice(_PW_CHARS) for _ in range(length))


def _render_create_user(actor_id: str) -> None:
    st.markdown("### ➕ Create New User")

    if "cu_gen_pw" not in st.session_state:
        st.session_state["cu_gen_pw"] = _gen_password()

    left, right = st.columns(2)

    with left:
        st.markdown("**Account Info**")
        email     = st.text_input("📧 Email *",        key="cu_email",
                                   placeholder="user@company.com")
        full_name = st.text_input("👤 Full Name *",    key="cu_name",
                                   placeholder="Your Name")
        company   = st.text_input("🏢 Company *",     key="cu_company",
                                   placeholder="Company Ltd")

    with right:
        st.markdown("**Tier & Password**")
        tier = st.selectbox(
            "Tier",
            options=["free", "pro", "admin"],
            format_func=lambda x: {"free": "🆓 Free (3 snapshots)",
                                    "pro":  "🔵 Pro (50 snapshots)",
                                    "admin":"🔴 Admin (unlimited)"  }[x],
            key="cu_tier",
        )

        auto_pw = st.toggle("🔐 Auto-generate password", value=True, key="cu_auto_pw")

        if auto_pw:
            pw = st.session_state["cu_gen_pw"]
            st.code(pw, language=None)
            st.caption("⚠️ Record this password — it cannot be viewed after creation")
            if st.button("🔄 Regenerate", key="cu_regen", use_container_width=True):
                st.session_state["cu_gen_pw"] = _gen_password()
                st.rerun()
        else:
            pw_a = st.text_input("🔒 Password *",    type="password", key="cu_pw_a",
                                  placeholder="Min 8 characters")
            pw_b = st.text_input("🔒 Confirm Password *", type="password", key="cu_pw_b",
                                  placeholder="Repeat password")
            pw = pw_a

    st.markdown("---")
    if st.button("✅ Create Account", type="primary",
                 use_container_width=True, key="cu_submit"):

        # ── Validate ──
        errors = []
        if not email.strip() or "@" not in email:
            errors.append("Invalid email")
        if not full_name.strip():
            errors.append("Name required")
        if not company.strip():
            errors.append("Company required")
        if not auto_pw:
            if len(pw_a) < 8:
                errors.append("Password must be at least 8 characters")
            elif pw_a != pw_b:
                errors.append("Passwords do not match")

        if errors:
            for e in errors:
                st.error(e)
            return

        # ── Create ──
        with st.spinner("Creating…"):
            try:
                import time
                user = create_user(
                    email.strip(), pw,
                    full_name.strip(), company.strip()
                )
                time.sleep(0.8)   # wait for DB trigger to build profile

                # Update tier if not Free
                if tier != "free":
                    update_user_tier(user.id, tier,
                                     _TIER_LIMITS[tier], actor_id)

                st.success(
                    f"✅ User created successfully!\n\n"
                    f"**Email:** {email}  \n"
                    f"**Tier:** {_TIER_CFG[tier]['label']}  \n"
                    f"**Password:** `{pw}`  \n\n"
                    f"Please send the password to the user securely."
                )
                # Clear form
                for k in ("cu_email", "cu_name", "cu_company",
                           "cu_gen_pw", "cu_pw_a", "cu_pw_b"):
                    st.session_state.pop(k, None)
                st.session_state["cu_gen_pw"] = _gen_password()

            except Exception as exc:
                err = str(exc).lower()
                if "already" in err or "exists" in err or "duplicate" in err:
                    st.error("❌ Email already registered")
                else:
                    st.error(f"❌ Creation failed: {exc}")


# ════════════════════════════════════════════════════════════════════════════
# Users tab
# ════════════════════════════════════════════════════════════════════════════

def _render_users(actor_id: str) -> None:
    users = get_all_users()
    if not users:
        st.info("No users found")
        return

    # ── Filters ──
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        q = st.text_input("🔍 Search (email / name / company)",
                          key="adm_search", placeholder="Search…")
    with fc2:
        tier_f = st.selectbox("Tier",
                              ["All", "free", "pro", "admin"],
                              key="adm_tier_f")

    if q:
        q_lo = q.lower()
        users = [u for u in users if
                 q_lo in (u.get("email")     or "").lower() or
                 q_lo in (u.get("full_name") or "").lower() or
                 q_lo in (u.get("company")   or "").lower()]
    if tier_f != "All":
        users = [u for u in users if u.get("tier") == tier_f]

    st.markdown(f"**{len(users)}** users found")

    for u in users:
        tier = u.get("tier", "free")
        tier_label = _TIER_CFG.get(tier, {}).get("label", tier)
        with st.expander(
            f"{tier_label} &nbsp;·&nbsp; **{u.get('full_name', '—')}** "
            f"&nbsp;·&nbsp; {u.get('email', '')} "
            f"&nbsp;·&nbsp; {u.get('company', '')}",
            expanded=False,
        ):
            _render_user_row(u, actor_id)


def _render_user_row(u: dict, actor_id: str) -> None:
    uid   = u["id"]
    tier  = u.get("tier", "free")
    limit = u.get("snapshot_limit", 3)

    # Info columns
    i1, i2, i3 = st.columns(3)
    with i1:
        st.markdown(f"**Email:** {u.get('email','')}")
        st.markdown(f"**Name:** {u.get('full_name','')}")
        st.markdown(f"**Company:** {u.get('company','')}")
    with i2:
        st.markdown(f"**Tier:** {_TIER_CFG.get(tier,{}).get('label', tier)}")
        st.markdown(f"**Snapshot Limit:** {limit if limit < 999999 else '∞'}")
        active = u.get("is_active", True)
        st.markdown(f"**Status:** {'✅ Active' if active else '🚫 Suspended'}")
    with i3:
        created = u.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            st.markdown(f"**Registered:** {dt.strftime('%Y-%m-%d')}")
        except Exception:
            st.markdown(f"**Registered:** {created[:10]}")
        last = u.get("last_login", "")
        if last:
            try:
                dt2 = datetime.fromisoformat(last.replace("Z", "+00:00"))
                st.markdown(f"**Last Login:** {dt2.strftime('%Y-%m-%d %H:%M')}")
            except Exception:
                pass

    # Cannot modify self
    if uid == actor_id:
        st.info("This is your own account")
        return

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)

    # Downgrade to Free
    with m1:
        if tier != "free":
            if st.button("⬇ Downgrade to Free", key=f"adm_free_{uid}",
                         use_container_width=True):
                update_user_tier(uid, "free", 3, actor_id)
                st.success("✅ Downgraded to Free")
                st.rerun()

    # Upgrade to Pro
    with m2:
        if tier != "pro":
            if st.button("🔵 Upgrade to Pro", key=f"adm_pro_{uid}",
                         type="primary", use_container_width=True):
                update_user_tier(uid, "pro", 50, actor_id)
                st.success("✅ Upgraded to Pro")
                st.rerun()

    # Custom snapshot limit
    with m3:
        new_lim = st.number_input(
            "Custom Limit",
            min_value=1, max_value=10000,
            value=int(limit) if limit < 999999 else 50,
            step=1,
            key=f"adm_lim_{uid}",
            label_visibility="collapsed",
        )
        if st.button("Set Limit", key=f"adm_setlim_{uid}",
                     use_container_width=True):
            update_user_tier(uid, tier, int(new_lim), actor_id)
            st.success(f"✅ Limit updated to {new_lim}")
            st.rerun()

    # Ban / Unban
    with m4:
        if u.get("is_active", True):
            if st.button("🚫 Suspend", key=f"adm_ban_{uid}",
                         use_container_width=True):
                st.session_state[f"_confirm_ban_{uid}"] = True
                st.rerun()
        else:
            if st.button("✅ Reactivate", key=f"adm_unban_{uid}",
                         use_container_width=True):
                set_user_active(uid, True, actor_id)
                st.success("✅ Account reactivated")
                st.rerun()

    # Ban confirm dialog
    if st.session_state.get(f"_confirm_ban_{uid}"):
        st.warning(f"Confirm suspend account {u.get('email')}?")
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("✅ Confirm Suspend", key=f"ban_ok_{uid}",
                         type="primary", use_container_width=True):
                set_user_active(uid, False, actor_id)
                st.session_state.pop(f"_confirm_ban_{uid}", None)
                st.success("✅ Account suspended")
                st.rerun()
        with bc2:
            if st.button("✖ Cancel", key=f"ban_cancel_{uid}",
                         use_container_width=True):
                st.session_state.pop(f"_confirm_ban_{uid}", None)
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# Stats tab
# ════════════════════════════════════════════════════════════════════════════

def _render_stats() -> None:
    stats = get_system_stats()
    if not stats:
        st.warning("Could not load stats")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Total Users",  stats.get("total_users", 0))
    c2.metric("🆓 Free",         stats.get("free_users",  0))
    c3.metric("🔵 Pro",          stats.get("pro_users",   0))
    c4.metric("🔴 Admin",        stats.get("admin_users", 0))
    c5.metric("📂 Snapshots",    stats.get("total_snaps", 0))


# ════════════════════════════════════════════════════════════════════════════
# Audit log tab
# ════════════════════════════════════════════════════════════════════════════

_ACTION_META: dict[str, tuple[str, str]] = {
    # action_key        → (icon,  display label)
    "login":            ("🔑", "Login"),
    "run_simulation":   ("⚡", "Run Simulation"),
    "export_report":    ("📊", "Export Report"),
    "export_csv":       ("📄", "Export CSV"),
    "tier_change":      ("🏷️", "Tier Change"),
    "activate":         ("✅", "Activate User"),
    "suspend":          ("🚫", "Suspend User"),
}
_ACTION_GROUPS: dict[str, list[str]] = {
    "All":        [],                                          # empty = no filter
    "Login":      ["login"],
    "Simulation": ["run_simulation"],
    "Export":     ["export_report", "export_csv"],
    "Admin":      ["tier_change", "activate", "suspend"],
}


def _fmt_detail(action: str, detail: dict) -> str:
    """Return a concise human-readable summary of the detail jsonb."""
    if not detail:
        return ""
    if action == "login":
        return detail.get("email", "")
    if action == "run_simulation":
        proj   = detail.get("project", "")
        pv     = detail.get("pv_kwp",  "")
        bess   = detail.get("bess_kwh","")
        npv    = detail.get("npv",     "")
        irr    = detail.get("irr",     "")
        parts  = []
        if proj:  parts.append(f"proj={proj}")
        if pv:    parts.append(f"PV={pv} kWp")
        if bess:  parts.append(f"BESS={bess} kWh")
        if npv:   parts.append(f"NPV={npv:,}" if isinstance(npv, (int, float)) else f"NPV={npv}")
        if irr:   parts.append(f"IRR={irr}%")
        return "  ·  ".join(parts)
    if action in ("export_report", "export_csv"):
        fname = detail.get("fname") or detail.get("project", "")
        return fname
    if action == "tier_change":
        return f"tier={detail.get('tier','')}  limit={detail.get('snapshot_limit','')}"
    # fallback
    return "  ·  ".join(f"{k}={v}" for k, v in detail.items())


def _render_audit_log() -> None:
    logs = get_audit_log(500)
    if not logs:
        st.info("No log entries")
        return

    # ── Action filter ──────────────────────────────────────────────────────
    fcol, _, rcol = st.columns([3, 5, 2])
    with fcol:
        filter_choice = st.radio(
            "Filter",
            options=list(_ACTION_GROUPS.keys()),
            horizontal=True,
            label_visibility="collapsed",
            key="audit_filter_radio",
        )
    with rcol:
        if st.button("🔄 Refresh", key="audit_refresh_btn", use_container_width=True):
            st.rerun()

    allowed_actions = _ACTION_GROUPS[filter_choice]

    rows = []
    for log in logs:
        action = log.get("action", "")
        if allowed_actions and action not in allowed_actions:
            continue

        try:
            dt = datetime.fromisoformat(log["created_at"].replace("Z", "+00:00"))
            ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts = (log.get("created_at") or "")[:19]

        actor_info = log.get("user_profiles") or {}
        email      = actor_info.get("email", (log.get("actor_id") or "?")[:8])
        name       = actor_info.get("full_name") or ""

        icon, label = _ACTION_META.get(action, ("•", action))
        detail_str  = _fmt_detail(action, log.get("detail") or {})

        rows.append({
            "Time":    ts,
            "User":    f"{name}  <{email}>" if name else email,
            "Action":  f"{icon} {label}",
            "Detail":  detail_str,
        })

    if not rows:
        st.info("No entries match the selected filter.")
        return

    df = pd.DataFrame(rows)
    st.caption(f"Showing {len(df)} entries  ·  maximum 500")
    st.dataframe(
        df,
        use_container_width=True,
        height=min(60 + len(df) * 35, 700),
        column_config={
            "Time":   st.column_config.TextColumn(width="medium"),
            "User":   st.column_config.TextColumn(width="medium"),
            "Action": st.column_config.TextColumn(width="small"),
            "Detail": st.column_config.TextColumn(width="large"),
        },
    )
