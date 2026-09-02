from pathlib import Path

import streamlit as st

from auth import require_login

_original_set_page_config = st.set_page_config


def _set_page_config_and_login(*args, **kwargs):
    result = _original_set_page_config(*args, **kwargs)
    require_login()
    return result


st.set_page_config = _set_page_config_and_login

main_path = Path(__file__).with_name("main.py")
exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"), globals(), globals())
