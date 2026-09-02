from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

import streamlit as st

AUTH_FILE = Path("/app/data/site_auth.json")
BOOTSTRAP_USERNAME = "jlb"
BOOTSTRAP_SALT_B64 = "yG/CWYisbZe7wtyiAJ7Lsg=="
BOOTSTRAP_HASH_B64 = "2knUDUeiz+1TJCgiwsFIXinZfWjSfj8X/z7Jgoxl29Q="
MAX_ATTEMPTS = 5
LOCK_SECONDS = 60


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )


def _load_credentials() -> dict:
    try:
        payload = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        if all(payload.get(key) for key in ("username", "salt", "hash")):
            return payload
    except Exception:
        pass
    return {
        "username": BOOTSTRAP_USERNAME,
        "salt": BOOTSTRAP_SALT_B64,
        "hash": BOOTSTRAP_HASH_B64,
        "bootstrap": True,
    }


def verify_credentials(username: str, password: str) -> bool:
    credentials = _load_credentials()
    if not hmac.compare_digest(str(username).strip(), str(credentials["username"])):
        return False
    try:
        salt = base64.b64decode(credentials["salt"])
        expected = base64.b64decode(credentials["hash"])
        actual = _derive(password, salt)
    except Exception:
        return False
    return hmac.compare_digest(actual, expected)


def save_credentials(username: str, password: str) -> None:
    username = str(username).strip()
    if len(username) < 2:
        raise ValueError("ユーザー名は2文字以上にしてください。")
    if len(password) < 12:
        raise ValueError("パスワードは12文字以上にしてください。")
    salt = secrets.token_bytes(16)
    digest = _derive(password, salt)
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = AUTH_FILE.with_suffix(".tmp")
    temp.write_text(
        json.dumps(
            {
                "username": username,
                "salt": base64.b64encode(salt).decode("ascii"),
                "hash": base64.b64encode(digest).decode("ascii"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temp.replace(AUTH_FILE)


def current_username() -> str:
    return str(_load_credentials().get("username") or BOOTSTRAP_USERNAME)


def using_bootstrap_credentials() -> bool:
    return bool(_load_credentials().get("bootstrap"))


def logout() -> None:
    for key in ("site_authenticated", "site_auth_user", "site_auth_attempts", "site_auth_locked_until"):
        st.session_state.pop(key, None)


def _render_login() -> None:
    st.markdown(
        """
<style>
[data-testid="stHeader"],[data-testid="stToolbar"],footer{display:none!important}
[data-testid="stAppViewContainer"]{background:#080b0e!important;color:#f4f6f8!important}
.block-container{max-width:520px!important;padding-top:11vh!important}
.login-shell{background:linear-gradient(180deg,#12171d,#0d1115);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:28px 30px 20px;box-shadow:0 24px 70px rgba(0,0,0,.35);margin-bottom:14px}
.login-brand{display:flex;align-items:center;gap:12px;margin-bottom:18px}.login-logo{width:44px;height:44px;border:2px solid #f0b82f;border-radius:50%;display:grid;place-items:center;color:#f0b82f;font-size:18px}.login-title{font-size:18px;font-weight:950;color:#f0b82f}.login-sub{font-size:9px;color:#9098a2;margin-top:3px}.login-copy{font-size:11px;color:#b7bec7;line-height:1.7;border-top:1px solid rgba(255,255,255,.08);padding-top:15px}
</style>
<div class="login-shell"><div class="login-brand"><div class="login-logo">⚾</div><div><div class="login-title">AI BASEBALL STUDIO</div><div class="login-sub">PRIVATE RESEARCH LOGIN</div></div></div><div class="login-copy">この研究サイトを閲覧するにはログインが必要です。</div></div>
""",
        unsafe_allow_html=True,
    )

    now = time.time()
    locked_until = float(st.session_state.get("site_auth_locked_until", 0) or 0)
    if locked_until > now:
        remaining = max(1, int(locked_until - now))
        st.error(f"ログイン試行回数が多いため、{remaining}秒後に再試行してください。")
        st.stop()

    with st.form("site_login", clear_on_submit=False):
        username = st.text_input("ユーザー名", autocomplete="username")
        password = st.text_input("パスワード", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("ログイン", type="primary", use_container_width=True)

    if submitted:
        if verify_credentials(username, password):
            st.session_state["site_authenticated"] = True
            st.session_state["site_auth_user"] = username.strip()
            st.session_state["site_auth_attempts"] = 0
            st.session_state["site_auth_locked_until"] = 0
            st.rerun()
        else:
            attempts = int(st.session_state.get("site_auth_attempts", 0) or 0) + 1
            st.session_state["site_auth_attempts"] = attempts
            if attempts >= MAX_ATTEMPTS:
                st.session_state["site_auth_attempts"] = 0
                st.session_state["site_auth_locked_until"] = time.time() + LOCK_SECONDS
                st.error("ログインに複数回失敗したため、一時的にロックしました。")
            else:
                st.error("ユーザー名またはパスワードが違います。")


def require_login() -> None:
    if st.session_state.get("site_authenticated") is True:
        return
    _render_login()
    st.stop()
