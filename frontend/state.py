import streamlit as st
from config import TONE_OPTIONS

# session_state초기화(입력 유지용)
def init_state():
    st.session_state.setdefault("product_name", "")
    st.session_state.setdefault("keywords_raw", "")
    st.session_state.setdefault("tone", TONE_OPTIONS[0])

    st.session_state.setdefault("image_bytes", None)
    st.session_state.setdefault("image_name", None)
    st.session_state.setdefault("image_type", None)

    st.session_state.setdefault("result", None)
    st.session_state.setdefault("output_format","png")

    st.session_state.setdefault("show_edit", False)
    st.session_state.setdefault("layout_label", "vertical")

