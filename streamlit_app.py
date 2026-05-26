import streamlit as st

st.set_page_config(page_title="SignalForge", page_icon="📡", layout="wide")

from app.storage.db import Database
from app.utils.config import load_config
from database.schema import init_db

init_db()

if "config" not in st.session_state:
    cfg = load_config()
    st.session_state.config = cfg
    st.session_state.db = Database()
    from app.utils.logging import setup_logging
    st.session_state.logger = setup_logging(cfg.logging.level, cfg.logging.file)

st.switch_page("pages/1_Dashboard.py")
