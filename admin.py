"""
admin.py — 管理员面板
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

    st.markdown("## 🔴 管理员面板 / Admin Panel")

    t_users, t_create, t_stats, t_log = st.tabs([
        "👥 用户管理 Users",
        "➕ 创建用户 Create",
        "📊 统计 Stats",
        "📋 操作日志 Audit Log",
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
    st.markdown("### ➕ 创建新用户 / Create New User")

    # ── 初始化生成的密码 ──
    if "cu_gen_pw" not in st.session_state:
        st.session_state["cu_gen_pw"] = _gen_password()

    left, right = st.columns(2)

    with left:
        st.markdown("**账号信息 Account Info**")
        email     = st.text_input("📧 邮箱 Email *",        key="cu_email",
                                   placeholder="user@company.com")
        full_name = st.text_input("👤 姓名 Full Name *",    key="cu_name",
                                   placeholder="张三 / Zhang San")
        company   = st.text_input("🏢 公司 Company *",     key="cu_company",
                                   placeholder="Company Ltd")

    with right:
        st.markdown("**权限 & 密码 Tier & Password**")
        tier = st.selectbox(
            "层级 Tier",
            options=["free", "pro", "admin"],
            format_func=lambda x: {"free": "🆓 Free (3 快照)",
                                    "pro":  "🔵 Pro (50 快照)",
                                    "admin":"🔴 Admin (无限)"   }[x],
            key="cu_tier",
        )

        auto_pw = st.toggle("🔐 自动生成密码", value=True, key="cu_auto_pw")

        if auto_pw:
            pw = st.session_state["cu_gen_pw"]
            st.code(pw, language=None)
            st.caption("⚠️ 请记录此密码，创建后无法再查看")
            if st.button("🔄 重新生成", key="cu_regen", use_container_width=True):
                st.session_state["cu_gen_pw"] = _gen_password()
                st.rerun()
        else:
            pw_a = st.text_input("🔒 密码 *",    type="password", key="cu_pw_a",
                                  placeholder="至少8位 / Min 8 chars")
            pw_b = st.text_input("🔒 确认密码 *", type="password", key="cu_pw_b",
                                  placeholder="再输一遍 / Repeat")
            pw = pw_a

    st.markdown("---")
    if st.button("✅ 立即创建账号", type="primary",
                 use_container_width=True, key="cu_submit"):

        # ── Validate ──
        errors = []
        if not email.strip() or "@" not in email:
            errors.append("邮箱格式无效 / Invalid email")
        if not full_name.strip():
            errors.append("请填写姓名 / Name required")
        if not company.strip():
            errors.append("请填写公司 / Company required")
        if not auto_pw:
            if len(pw_a) < 8:
                errors.append("密码至少8位 / Password ≥ 8 chars")
            elif pw_a != pw_b:
                errors.append("两次密码不一致 / Passwords do not match")

        if errors:
            for e in errors:
                st.error(e)
            return

        # ── Create ──
        with st.spinner("创建中… / Creating…"):
            try:
                import time
                user = create_user(
                    email.strip(), pw,
                    full_name.strip(), company.strip()
                )
                time.sleep(0.8)   # 等待 DB trigger 建立 profile

                # 非 Free 层级时更新 tier
                if tier != "free":
                    update_user_tier(user.id, tier,
                                     _TIER_LIMITS[tier], actor_id)

                st.success(
                    f"✅ 用户创建成功！\n\n"
                    f"**邮箱:** {email}  \n"
                    f"**层级:** {_TIER_CFG[tier]['label']}  \n"
                    f"**密码:** `{pw}`  \n\n"
                    f"请将密码安全地发送给用户。"
                )
                # 清空表单
                for k in ("cu_email", "cu_name", "cu_company",
                           "cu_gen_pw", "cu_pw_a", "cu_pw_b"):
                    st.session_state.pop(k, None)
                st.session_state["cu_gen_pw"] = _gen_password()

            except Exception as exc:
                err = str(exc).lower()
                if "already" in err or "exists" in err or "duplicate" in err:
                    st.error("❌ 该邮箱已被注册 / Email already exists")
                else:
                    st.error(f"❌ 创建失败 / Failed: {exc}")


# ════════════════════════════════════════════════════════════════════════════
# Users tab
# ════════════════════════════════════════════════════════════════════════════

def _render_users(actor_id: str) -> None:
    users = get_all_users()
    if not users:
        st.info("暂无用户 / No users found")
        return

    # ── Filters ──
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        q = st.text_input("🔍 搜索 Search (email / name / company)",
                          key="adm_search", placeholder="Search…")
    with fc2:
        tier_f = st.selectbox("层级 Tier",
                              ["全部 All", "free", "pro", "admin"],
                              key="adm_tier_f")

    if q:
        q_lo = q.lower()
        users = [u for u in users if
                 q_lo in (u.get("email")     or "").lower() or
                 q_lo in (u.get("full_name") or "").lower() or
                 q_lo in (u.get("company")   or "").lower()]
    if tier_f != "全部 All":
        users = [u for u in users if u.get("tier") == tier_f]

    st.markdown(f"**{len(users)}** 个用户匹配 / users found")

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
        st.markdown(f"**姓名:** {u.get('full_name','')}")
        st.markdown(f"**公司:** {u.get('company','')}")
    with i2:
        st.markdown(f"**层级 Tier:** {_TIER_CFG.get(tier,{}).get('label', tier)}")
        st.markdown(f"**快照配额:** {limit if limit < 999999 else '∞'}")
        active = u.get("is_active", True)
        st.markdown(f"**账号状态:** {'✅ 正常' if active else '🚫 已停用'}")
    with i3:
        created = u.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            st.markdown(f"**注册:** {dt.strftime('%Y-%m-%d')}")
        except Exception:
            st.markdown(f"**注册:** {created[:10]}")
        last = u.get("last_login", "")
        if last:
            try:
                dt2 = datetime.fromisoformat(last.replace("Z", "+00:00"))
                st.markdown(f"**最后登录:** {dt2.strftime('%Y-%m-%d %H:%M')}")
            except Exception:
                pass

    # Cannot modify self
    if uid == actor_id:
        st.info("当前登录账号 / This is your own account")
        return

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)

    # Downgrade to Free
    with m1:
        if tier != "free":
            if st.button("⬇ 降为 Free", key=f"adm_free_{uid}",
                         use_container_width=True):
                update_user_tier(uid, "free", 3, actor_id)
                st.success("✅ 已降为 Free")
                st.rerun()

    # Upgrade to Pro
    with m2:
        if tier != "pro":
            if st.button("🔵 升为 Pro", key=f"adm_pro_{uid}",
                         type="primary", use_container_width=True):
                update_user_tier(uid, "pro", 50, actor_id)
                st.success("✅ 已升级为 Pro")
                st.rerun()

    # Custom snapshot limit
    with m3:
        new_lim = st.number_input(
            "自定义配额",
            min_value=1, max_value=10000,
            value=int(limit) if limit < 999999 else 50,
            step=1,
            key=f"adm_lim_{uid}",
            label_visibility="collapsed",
        )
        if st.button("设配额", key=f"adm_setlim_{uid}",
                     use_container_width=True):
            update_user_tier(uid, tier, int(new_lim), actor_id)
            st.success(f"✅ 配额已改为 {new_lim}")
            st.rerun()

    # Ban / Unban
    with m4:
        if u.get("is_active", True):
            if st.button("🚫 停用", key=f"adm_ban_{uid}",
                         use_container_width=True):
                st.session_state[f"_confirm_ban_{uid}"] = True
                st.rerun()
        else:
            if st.button("✅ 恢复", key=f"adm_unban_{uid}",
                         use_container_width=True):
                set_user_active(uid, True, actor_id)
                st.success("✅ 账号已恢复")
                st.rerun()

    # Ban confirm dialog
    if st.session_state.get(f"_confirm_ban_{uid}"):
        st.warning(f"确认停用账号 {u.get('email')} ? / Confirm suspend?")
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("✅ 确认停用", key=f"ban_ok_{uid}",
                         type="primary", use_container_width=True):
                set_user_active(uid, False, actor_id)
                st.session_state.pop(f"_confirm_ban_{uid}", None)
                st.success("✅ 已停用")
                st.rerun()
        with bc2:
            if st.button("✖ 取消", key=f"ban_cancel_{uid}",
                         use_container_width=True):
                st.session_state.pop(f"_confirm_ban_{uid}", None)
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# Stats tab
# ════════════════════════════════════════════════════════════════════════════

def _render_stats() -> None:
    stats = get_system_stats()
    if not stats:
        st.warning("无法获取统计数据 / Could not load stats")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 总用户 Users",     stats.get("total_users", 0))
    c2.metric("🆓 Free",             stats.get("free_users",  0))
    c3.metric("🔵 Pro",              stats.get("pro_users",   0))
    c4.metric("🔴 Admin",            stats.get("admin_users", 0))
    c5.metric("📂 快照总数 Snapshots", stats.get("total_snaps", 0))


# ════════════════════════════════════════════════════════════════════════════
# Audit log tab
# ════════════════════════════════════════════════════════════════════════════

def _render_audit_log() -> None:
    logs = get_audit_log(200)
    if not logs:
        st.info("暂无日志 / No log entries")
        return

    rows = []
    for log in logs:
        try:
            dt = datetime.fromisoformat(
                log["created_at"].replace("Z", "+00:00"))
            ts = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts = (log.get("created_at") or "")[:16]

        actor_info  = log.get("user_profiles") or {}
        actor_email = actor_info.get("email", (log.get("actor_id") or "?")[:8])

        rows.append({
            "时间 Time":     ts,
            "操作者 Actor":  actor_email,
            "动作 Action":   log.get("action", ""),
            "详情 Detail":   str(log.get("detail") or {}),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=420)
