"""
auth.py — Login / Registration / Email Verification UI + Session helpers
BTM PV+BESS Financial Modelling System
"""

from __future__ import annotations

import re
import streamlit as st

from db import (sign_up, sign_in, refresh_session, verify_otp, resend_verification,
                sign_out, get_user_profile, update_last_login, _secrets_ok,
                log_user_action)


# ── localStorage keys for "remember me" ──────────────────────────────────────
_LS_KEY       = "btm_auth_v2"   # full session  {e, rt, ts}
_LS_EMAIL_KEY = "btm_email_v1"  # email-only, persists even after token expiry


def _st_html_js(html_snippet: str) -> None:
    """Version-safe JS injection via st.html().

    Streamlit ≥1.37 requires ``unsafe_allow_javascript=True``; older builds
    execute inline <script> tags by default and reject the kwarg.  This wrapper
    tries the modern form first and falls back silently.
    """
    try:
        st.html(html_snippet, unsafe_allow_javascript=True)
    except TypeError:
        st.html(html_snippet)          # pre-1.37: scripts execute without the kwarg


def _js_save_session(email: str, refresh_token: str) -> None:
    """Persist email + refresh_token (and email-only key) to browser localStorage."""
    safe_e  = email.replace("\\", "\\\\").replace('"', '\\"')
    safe_rt = refresh_token.replace("\\", "\\\\").replace('"', '\\"')
    _st_html_js(f"""<script>
(function(){{
  try{{
    localStorage.setItem('{_LS_KEY}', JSON.stringify({{
      e:"{safe_e}", rt:"{safe_rt}", ts:Date.now()
    }}));
    // Save email separately so prefill works even after token expiry
    localStorage.setItem('{_LS_EMAIL_KEY}', "{safe_e}");
  }}catch(ex){{ console.warn('BTM auth-save error:', ex); }}
}})();
</script>""")


def _js_clear_session() -> None:
    """Remove saved session (token) from browser localStorage.
    Keeps the email-only key so the form stays pre-filled after logout.
    """
    _st_html_js(f"""<script>
(function(){{
  try{{ localStorage.removeItem('{_LS_KEY}'); }}catch(ex){{}}
}})();
</script>""")


def flush_token_to_storage() -> None:
    """Execute a deferred localStorage save or clear.

    MUST be called from a *stable* render — i.e. a render that does NOT
    immediately call st.rerun() afterwards.  Calling components.html()
    right before st.rerun() races: Streamlit starts the new render before
    the iframe's JS has time to execute, so the write silently never
    happens.

    Pattern:
      - Login / auto-login → set  st.session_state["_ls_cmd"] = ("save", email, token)
      - Logout             → set  st.session_state["_ls_cmd"] = ("clear",)
      - app.py calls flush_token_to_storage() once, right after the auth gate,
        in the first stable logged-in render.
    """
    cmd = st.session_state.pop("_ls_cmd", None)
    if cmd is None:
        return
    if cmd[0] == "save" and len(cmd) == 3:
        _js_save_session(cmd[1], cmd[2])
    elif cmd[0] == "clear":
        _js_clear_session()


def _inject_auth_loader() -> None:
    """JS bridge: read localStorage → redirect with token (auto-login) or email (prefill).

    Priority:
      1. Full token in btm_auth_v2  → ?_btm_rt=<token>&_btm_e=<email>  (auto-login)
      2. Email-only in btm_email_v1 → ?_btm_e=<email>                  (form prefill)

    Runs in the main page DOM (not iframe) via st.html() so window.location
    works without sandbox restrictions.  Delay of 700 ms gives Streamlit's
    React tree time to mount before the redirect fires.
    """
    _st_html_js(f"""<script>
(function(){{
  setTimeout(function(){{
    try{{
      var url = new URL(window.location.href);
      // Already bridged — don't loop
      if(url.searchParams.has('_btm_rt') || url.searchParams.has('_btm_e')){{ return; }}

      // ── Try full auto-login (token + email) ──────────────────────────────
      var raw = localStorage.getItem('{_LS_KEY}');
      if(raw){{
        var auth;
        try{{ auth = JSON.parse(raw); }}catch(e){{ localStorage.removeItem('{_LS_KEY}'); }}
        if(auth && auth.rt && (Date.now() - (auth.ts||0)) < 30*86400000){{
          url.searchParams.set('_btm_rt', auth.rt);
          url.searchParams.set('_btm_e',  auth.e || '');
          window.location.replace(url.href);
          return;
        }} else {{
          localStorage.removeItem('{_LS_KEY}');   // expired — wipe token
        }}
      }}

      // ── Fallback: email-only prefill ─────────────────────────────────────
      var savedEmail = localStorage.getItem('{_LS_EMAIL_KEY}');
      if(savedEmail){{
        url.searchParams.set('_btm_e', savedEmail);
        window.location.replace(url.href);
      }}
    }}catch(ex){{ console.warn('BTM auth-loader error:', ex); }}
  }}, 700);
}})();
</script>""")


def _inject_autocomplete() -> None:
    """Enable browser-native autocomplete on the email + password inputs."""
    _st_html_js("""<script>
setTimeout(function(){
  try{
    var found = 0;
    document.querySelectorAll('input').forEach(function(inp){
      if(found===0 && (inp.type==='text' || inp.type==='email')){
        inp.setAttribute('autocomplete','username');
        inp.setAttribute('name','username');
        inp.setAttribute('type','email');
        found=1;
      } else if(found===1 && inp.type==='password'){
        inp.setAttribute('autocomplete','current-password');
        inp.setAttribute('name','password');
        found=2;
      }
    });
  }catch(e){}
}, 600);
</script>""")


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
    for k in ("_user_profile", "_auth_mode", "_pending_email",
              "_btm_ls_checked"):
        st.session_state.pop(k, None)
    # Queue the clear — render_auth_gate() will execute it in the next stable
    # render (login page).  Calling _js_clear_session() here directly would
    # race with st.rerun(): the iframe JS never fires before the page changes.
    st.session_state["_ls_cmd"] = ("clear",)
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
    # ── Deferred localStorage clear (queued by logout()) ─────────────────────
    # logout() can't call _js_clear_session() directly before st.rerun()
    # because the iframe JS races with the rerun.  It queues ("clear",) here
    # so the clear runs in this stable render (no immediate rerun follows).
    _deferred = st.session_state.pop("_ls_cmd", None)
    if _deferred is not None and _deferred[0] == "clear":
        _js_clear_session()

    # ── Auto-login or email-prefill from localStorage bridge ─────────────────
    # The JS loader (injected below) redirects to ?_btm_rt=<token>&_btm_e=<email>
    # for auto-login, OR to ?_btm_e=<email> (no _btm_rt) for email-only prefill.
    # Guard _btm_ls_checked so we handle this at most once per Streamlit session.

    _rt    = st.query_params.get("_btm_rt", "")
    _email = st.query_params.get("_btm_e",  "")

    if (_rt or _email) and "_btm_ls_checked" not in st.session_state:
        st.session_state["_btm_ls_checked"] = True
        # Clear params from URL before any rerun
        for _p in ("_btm_rt", "_btm_e"):
            try:
                del st.query_params[_p]
            except Exception:
                pass

        if _rt:
            # ── Full auto-login attempt ──────────────────────────────────────
            with st.spinner("Signing in…"):
                resp = refresh_session(_rt)
                if resp and resp.session:
                    # Token valid: rotate + defer save
                    st.session_state["_ls_cmd"] = ("save", _email, resp.session.refresh_token)
                    _on_login_success(resp, _email)
                    return
            # Token expired: clear the stale token, keep the email for prefill
            _js_clear_session()
            if _email:
                st.session_state["_btm_prefill_email"] = _email
            st.info("Session expired — please sign in again")
        elif _email:
            # ── Email-only prefill (no token) ────────────────────────────────
            st.session_state["_btm_prefill_email"] = _email

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

    st.markdown("#### Sign In")

    # ── Auto-login bridge: inject loader ONCE per session ──
    # Set the guard flag BEFORE injecting so that if the JS redirect fails
    # silently (cross-origin block, empty localStorage, etc.) we don't keep
    # re-injecting the loader on every subsequent Streamlit rerun.
    _ls_checked = st.session_state.get("_btm_ls_checked", False)
    if (not _ls_checked
            and "_btm_rt" not in st.query_params
            and "_btm_e"  not in st.query_params):
        st.session_state["_btm_ls_checked"] = True   # mark before inject
        _inject_auth_loader()   # JS: read localStorage → window.location.replace redirect

    # Pre-filled email (set on returning visits or when token expires)
    _prefill = st.session_state.pop("_btm_prefill_email", "")

    # Enable browser-native autocomplete so Chrome/Firefox can save passwords
    _inject_autocomplete()

    email    = st.text_input("📧 Email",    key="li_email",
                              value=_prefill,
                              placeholder="your@email.com")
    password = st.text_input("🔒 Password", key="li_password",
                              type="password", placeholder="••••••••")

    rm_col, _ = st.columns([3, 2])
    with rm_col:
        remember_me = st.checkbox(
            "Remember me  (30 days)",
            value=True,          # default ON — user must actively uncheck to opt out
            key="li_remember",
            help="Stay signed in for 30 days on this browser",
        )

    login_col, reg_col = st.columns(2)
    with login_col:
        login_clicked = st.button("Sign In", type="primary",
                                  use_container_width=True, key="li_btn")
    with reg_col:
        if st.button("Register", use_container_width=True, key="li_reg_btn"):
            st.session_state["_auth_mode"] = "register"
            st.rerun()

    if login_clicked:
        if not email.strip() or not password:
            st.error("Please enter email and password")
            return
        with st.spinner("Signing in…"):
            try:
                resp = sign_in(email.strip(), password)
                # ── Remember Me ────────────────────────────────────────────
                # Queue the localStorage op so it runs in the first *stable*
                # logged-in render (flush_token_to_storage in app.py).
                # Direct calls here race with the st.rerun() inside
                # _on_login_success: the iframe JS never executes.
                if remember_me and resp and resp.session:
                    st.session_state["_ls_cmd"] = ("save", email.strip(),
                                                    resp.session.refresh_token)
                else:
                    st.session_state["_ls_cmd"] = ("clear",)
                _on_login_success(resp, email.strip())
            except Exception as exc:
                _handle_login_error(exc, email.strip())


def _on_login_success(resp, email: str):
    if not resp.user:
        st.error("Login failed")
        return

    # Note: email_confirmed_at check intentionally removed.
    # If Supabase email confirmation is disabled, confirmed_at is None but
    # login still succeeds.  If re-enabled later, Supabase rejects unconfirmed
    # logins at the API level — we handle that in _handle_login_error().

    profile = get_user_profile(resp.user.id)
    if not profile:
        st.error("Profile missing — contact admin")
        return
    if not profile.get("is_active", True):
        st.error("Account suspended — contact admin")
        return

    st.session_state["_user_profile"] = profile
    update_last_login(resp.user.id)
    log_user_action(resp.user.id, "login", {"email": email})
    st.rerun()


def _handle_login_error(exc: Exception, email: str):
    err = str(exc).lower()
    if "invalid login" in err or "invalid_credentials" in err or "invalid" in err:
        st.error("Invalid email or password")
    elif "email not confirmed" in err or "not confirmed" in err:
        st.session_state["_pending_email"] = email
        st.session_state["_auth_mode"]    = "verify"
        st.warning("Email not confirmed")
        st.rerun()
    elif "too many" in err:
        st.error("Too many requests — please try again later")
    else:
        st.error(f"Sign-in failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────────────────────────────────────

def _render_register():
    st.markdown("""
    <div class="auth-logo">
        <div class="icon">⚡</div>
        <div class="title">BTM Solar+BESS</div>
        <div class="sub">Create Account</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Register")

    full_name = st.text_input("👤 Full Name *",    key="reg_name",
                               placeholder="Your Name")
    company   = st.text_input("🏢 Company *",     key="reg_company",
                               placeholder="Your Company Ltd")
    email     = st.text_input("📧 Email *",       key="reg_email",
                               placeholder="your@email.com")
    password  = st.text_input("🔒 Password *",    key="reg_pw",
                               type="password", placeholder="Min 8 characters")
    password2 = st.text_input("🔒 Confirm Password *", key="reg_pw2",
                               type="password", placeholder="Repeat password")

    st.markdown("""<div class="tier-info">
        New accounts are Free tier (3 snapshots). Contact admin to upgrade to Pro.
    </div>""", unsafe_allow_html=True)

    btn_col, back_col = st.columns(2)
    with btn_col:
        create_clicked = st.button("Create Account", type="primary",
                                   use_container_width=True, key="reg_create_btn")
    with back_col:
        if st.button("Back to Sign In", use_container_width=True, key="reg_back_btn"):
            st.session_state["_auth_mode"] = "login"
            st.rerun()

    if create_clicked:
        errors = []
        if not full_name.strip():
            errors.append("Name required")
        if not company.strip():
            errors.append("Company required")
        if not _valid_email(email):
            errors.append("Invalid email format")
        if not _valid_password(password):
            errors.append("Password must be at least 8 characters")
        if password != password2:
            errors.append("Passwords do not match")

        if errors:
            for e in errors:
                st.error(e)
            return

        with st.spinner("Creating account…"):
            try:
                resp = sign_up(email.strip(), password,
                               full_name.strip(), company.strip())

                if resp.session:
                    # Email confirmation disabled — user is immediately active
                    import time; time.sleep(0.8)   # wait for DB trigger
                    profile = get_user_profile(resp.user.id)
                    if profile:
                        st.session_state["_user_profile"] = profile
                        update_last_login(resp.user.id)
                        st.success("✅ Account created successfully!")
                        st.rerun()
                    else:
                        st.error("Account created but profile load failed — please sign in")
                        st.session_state["_auth_mode"] = "login"
                        st.rerun()
                else:
                    # Email confirmation required — go to OTP verify
                    st.session_state["_pending_email"] = email.strip()
                    st.session_state["_auth_mode"]     = "verify"
                    st.rerun()

            except Exception as exc:
                err = str(exc).lower()
                if "already registered" in err or "already been registered" in err:
                    st.error("Email already registered")
                else:
                    st.error(f"Registration failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# OTP Verify
# ─────────────────────────────────────────────────────────────────────────────

def _render_verify():
    pending = st.session_state.get("_pending_email", "")

    st.markdown("""
    <div class="auth-logo">
        <div class="icon">📬</div>
        <div class="title">Email Verification</div>
        <div class="sub">Verify your email address</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div class="auth-otp-box">
        Verification code sent to:<br>
        <b>{pending}</b><br><br>
        Check your inbox and enter the 6-digit code below.
        <br><small style='color:#667'>(Check spam if not received)</small>
    </div>""", unsafe_allow_html=True)

    otp = st.text_input("Verification Code", key="otp_input",
                        max_chars=6, placeholder="123456")

    v_col, resend_col, back_col = st.columns([3, 2, 2])
    with v_col:
        verify_clicked = st.button("✅ Verify", type="primary",
                                   use_container_width=True, key="otp_verify_btn")
    with resend_col:
        if st.button("Resend Code", use_container_width=True, key="otp_resend_btn"):
            try:
                resend_verification(pending)
                st.success("Code resent")
            except Exception as exc:
                st.error(str(exc))
    with back_col:
        if st.button("Back", use_container_width=True, key="otp_back_btn"):
            st.session_state["_auth_mode"] = "login"
            st.rerun()

    if verify_clicked:
        otp_val = otp.strip()
        if len(otp_val) != 6 or not otp_val.isdigit():
            st.error("Please enter the 6-digit numeric code")
            return
        with st.spinner("Verifying…"):
            try:
                resp = verify_otp(pending, otp_val)
                if not resp.user:
                    st.error("Verification failed")
                    return
                profile = get_user_profile(resp.user.id)
                if profile:
                    st.session_state["_user_profile"] = profile
                    update_last_login(resp.user.id)
                    st.session_state.pop("_pending_email", None)
                    st.session_state.pop("_auth_mode",    None)
                    st.success("✅ Verified! Loading…")
                    st.rerun()
                else:
                    st.error("Profile load failed — please refresh and try again")
            except Exception as exc:
                err = str(exc).lower()
                if "expired" in err or "invalid" in err or "otp" in err:
                    st.error("Invalid or expired code")
                else:
                    st.error(f"Verification error: {exc}")
