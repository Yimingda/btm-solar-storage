"""
auth.py — 登录 / 注册 / 邮件验证 UI + Session helpers
BTM PV+BESS Financial Modelling System
"""

from __future__ import annotations

import re
import streamlit as st
from db import (sign_up, sign_in, verify_otp, resend_verification,
                sign_out, get_user_profile, update_last_login, _secrets_ok)


# ════════════════════════════════════════════════════════════════════════════
# Session helpers
# ════════════════════════════════════════════════════════════════════════════

def is_logged_in() -> bool:
    """True when a verified user profile exists in session state."""
    if not _secrets_ok():
        return True   # Dev mode: secrets not configured → bypass auth
    return bool(st.session_state.get("_user_profile"))


def get_current_user() -> dict | None:
    return st.session_state.get("_user_profile")


def get_tier() -> str:
    u = get_current_user()
    return u.get("tier", "free") if u else "free"


def is_pro() -> bool:
    return get_tier() in ("pro", "admin")


def is_admin() -> bool:
    return get_tier() == "admin"


def logout():
    sign_out()
    for k in ("_user_profile", "_auth_mode", "_pending_email"):
        st.session_state.pop(k, None)
    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# Input validation
# ════════════════════════════════════════════════════════════════════════════

def _valid_email(email: str) -> bool:
    return bool(re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()))


def _valid_password(pw: str) -> bool:
    return len(pw) >= 8


# ════════════════════════════════════════════════════════════════════════════
# Auth gate renderer  (called from app.py when not logged in)
# ════════════════════════════════════════════════════════════════════════════

# Shared CSS injected once
_AUTH_CSS = """
<style>
.auth-card {
    max-width: 440px;
    margin: 0 auto;
    padding: 36px 40px 40px;
    border-radius: 14px;
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.auth-logo { text-align:center; margin-bottom:20px; }
.auth-logo .icon { font-size:2.4rem; }
.auth-logo .title {
    font-size:1.4rem; font-weight:700;
    color:#00e5a0; margin:6px 0 2px;
}
.auth-logo .sub { color:#778; font-size:0.82rem; }
.auth-divider { color:#445; text-align:center; margin:12px 0; font-size:0.8rem; }
.auth-otp-box {
    background:#1e3a2f; border-left:4px solid #00e5a0;
    border-radius:6px; padding:14px 16px;
    color:#ccd; font-size:0.88rem; margin-bottom:14px;
}
.auth-otp-box b { color:#00e5a0; }
.tier-info {
    background:#1e1e3a; border-left:3px solid #4488ff;
    border-radius:6px; padding:10px 14px;
    color:#99a; font-size:0.8rem; margin-top:10px;
}
</style>
"""


def render_auth_gate():
    """
    Full-page auth UI.  Renders in the centre of the wide-layout page.
    Caller must call st.stop() after this.
    """
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    # Centre with columns
    _, centre, _ = st.columns([1, 1.6, 1])
    with centre:
        mode = st.session_state.get("_auth_mode", "login")
        if   mode == "login":    _render_login()
        elif mode == "register": _render_register()
        elif mode == "verify":   _render_verify()


# ─────────────────────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────────────────────

def _render_login():
    st.markdown("""
    <div class="auth-logo">
        <div class="icon">⚡</div>
        <div class="title">BTM Solar+BESS</div>
        <div class="sub">Financial Modelling System</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 登录 Sign In")

    email    = st.text_input("📧 邮箱 Email",    key="li_email",
                              placeholder="your@email.com")
    password = st.text_input("🔒 密码 Password", key="li_password",
                              type="password", placeholder="••••••••")

    login_col, reg_col = st.columns(2)
    with login_col:
        login_clicked = st.button("登录 Sign In", type="primary",
                                  use_container_width=True, key="li_btn")
    with reg_col:
        if st.button("注册 Register", use_container_width=True, key="li_reg_btn"):
            st.session_state["_auth_mode"] = "register"
            st.rerun()

    if login_clicked:
        if not email.strip() or not password:
            st.error("请填写邮箱和密码 / Please enter email and password")
            return
        with st.spinner("登录中 / Signing in…"):
            try:
                resp = sign_in(email.strip(), password)
                _on_login_success(resp, email.strip())
            except Exception as exc:
                _handle_login_error(exc, email.strip())


def _on_login_success(resp, email: str):
    if not resp.user:
        st.error("登录失败 / Login failed")
        return

    # Check email confirmed
    if not resp.user.email_confirmed_at:
        st.session_state["_pending_email"] = email
        st.session_state["_auth_mode"]    = "verify"
        st.warning("邮箱未验证，请输入验证码 / Email not confirmed — enter your OTP")
        st.rerun()
        return

    profile = get_user_profile(resp.user.id)
    if not profile:
        st.error("账号数据异常，请联系管理员 / Profile missing — contact admin")
        return
    if not profile.get("is_active", True):
        st.error("账号已被停用 / Account suspended — contact admin")
        return

    st.session_state["_user_profile"] = profile
    update_last_login(resp.user.id)
    st.rerun()


def _handle_login_error(exc: Exception, email: str):
    err = str(exc).lower()
    if "invalid login" in err or "invalid_credentials" in err or "invalid" in err:
        st.error("邮箱或密码错误 / Invalid email or password")
    elif "email not confirmed" in err or "not confirmed" in err:
        st.session_state["_pending_email"] = email
        st.session_state["_auth_mode"]    = "verify"
        st.warning("邮箱未验证 / Email not confirmed")
        st.rerun()
    elif "too many" in err:
        st.error("请求过于频繁，请稍后再试 / Too many requests, try later")
    else:
        st.error(f"登录失败 / Login failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────────────────────────────────────

def _render_register():
    st.markdown("""
    <div class="auth-logo">
        <div class="icon">⚡</div>
        <div class="title">BTM Solar+BESS</div>
        <div class="sub">创建账号 / Create Account</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 注册新账号 Register")

    full_name = st.text_input("👤 姓名 Full Name *",    key="reg_name",
                               placeholder="张三 / Zhang San")
    company   = st.text_input("🏢 公司 Company *",     key="reg_company",
                               placeholder="Your Company Ltd")
    email     = st.text_input("📧 邮箱 Email *",       key="reg_email",
                               placeholder="your@email.com")
    password  = st.text_input("🔒 密码 Password *",    key="reg_pw",
                               type="password", placeholder="至少8位 / Min 8 chars")
    password2 = st.text_input("🔒 确认密码 Confirm *", key="reg_pw2",
                               type="password", placeholder="再输一遍 / Repeat")

    st.markdown("""<div class="tier-info">
        注册后默认为 🆓 免费账号（3个快照）。如需 🔵 Pro 版请联系管理员升级。<br>
        New accounts are Free tier (3 snapshots). Contact admin to upgrade to Pro.
    </div>""", unsafe_allow_html=True)

    btn_col, back_col = st.columns(2)
    with btn_col:
        create_clicked = st.button("创建账号 Create", type="primary",
                                   use_container_width=True, key="reg_create_btn")
    with back_col:
        if st.button("返回登录 Back", use_container_width=True, key="reg_back_btn"):
            st.session_state["_auth_mode"] = "login"
            st.rerun()

    if create_clicked:
        errors = []
        if not full_name.strip():
            errors.append("请填写姓名 / Name required")
        if not company.strip():
            errors.append("请填写公司名 / Company required")
        if not _valid_email(email):
            errors.append("邮箱格式无效 / Invalid email format")
        if not _valid_password(password):
            errors.append("密码至少8位 / Password must be ≥ 8 characters")
        if password != password2:
            errors.append("两次密码不一致 / Passwords do not match")

        if errors:
            for e in errors:
                st.error(e)
            return

        with st.spinner("创建账号中 / Creating account…"):
            try:
                sign_up(email.strip(), password,
                        full_name.strip(), company.strip())
                st.session_state["_pending_email"] = email.strip()
                st.session_state["_auth_mode"]     = "verify"
                st.rerun()
            except Exception as exc:
                err = str(exc).lower()
                if "already registered" in err or "already been registered" in err:
                    st.error("该邮箱已注册 / Email already registered")
                else:
                    st.error(f"注册失败 / Registration failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# OTP Verify
# ─────────────────────────────────────────────────────────────────────────────

def _render_verify():
    pending = st.session_state.get("_pending_email", "")

    st.markdown("""
    <div class="auth-logo">
        <div class="icon">📬</div>
        <div class="title">验证邮箱</div>
        <div class="sub">Email Verification</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div class="auth-otp-box">
        验证码已发送至 / Code sent to:<br>
        <b>{pending}</b><br><br>
        请查收邮件并输入6位数字验证码。<br>
        Check your inbox and enter the 6-digit code below.
        <br><small style='color:#667'>（如未收到请检查垃圾邮件 / Check spam if not received）</small>
    </div>""", unsafe_allow_html=True)

    otp = st.text_input("验证码 Verification Code", key="otp_input",
                        max_chars=6, placeholder="123456")

    v_col, resend_col, back_col = st.columns([3, 2, 2])
    with v_col:
        verify_clicked = st.button("✅ 验证 Verify", type="primary",
                                   use_container_width=True, key="otp_verify_btn")
    with resend_col:
        if st.button("重发 Resend", use_container_width=True, key="otp_resend_btn"):
            try:
                resend_verification(pending)
                st.success("已重发 / Code resent")
            except Exception as exc:
                st.error(str(exc))
    with back_col:
        if st.button("返回 Back", use_container_width=True, key="otp_back_btn"):
            st.session_state["_auth_mode"] = "login"
            st.rerun()

    if verify_clicked:
        otp_val = otp.strip()
        if len(otp_val) != 6 or not otp_val.isdigit():
            st.error("请输入6位数字验证码 / Enter the 6-digit numeric code")
            return
        with st.spinner("验证中 / Verifying…"):
            try:
                resp = verify_otp(pending, otp_val)
                if not resp.user:
                    st.error("验证失败 / Verification failed")
                    return
                profile = get_user_profile(resp.user.id)
                if profile:
                    st.session_state["_user_profile"] = profile
                    update_last_login(resp.user.id)
                    st.session_state.pop("_pending_email", None)
                    st.session_state.pop("_auth_mode",    None)
                    st.success("✅ 验证成功！正在进入系统… / Verified! Loading…")
                    st.rerun()
                else:
                    st.error("验证成功但档案读取失败，请刷新重试 / Profile load failed, refresh and try again")
            except Exception as exc:
                err = str(exc).lower()
                if "expired" in err or "invalid" in err or "otp" in err:
                    st.error("验证码无效或已过期 / Invalid or expired code")
                else:
                    st.error(f"验证失败 / Verification error: {exc}")
