from __future__ import annotations

from contextlib import contextmanager
from html import escape
from typing import Iterator

import streamlit as st


@contextmanager
def form_loading(message: str) -> Iterator[None]:
    placeholder = st.empty()
    placeholder.markdown(
        f"""
        <div class="form-loading" role="status" aria-live="polite">
            <span class="form-loading-spinner"></span>
            <span>{escape(message)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        placeholder.empty()
