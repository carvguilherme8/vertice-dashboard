import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import theme  # noqa: E402
from views import painel  # noqa: E402

st.set_page_config(
    page_title="Painel Único de Decisão Comercial · Vértice",
    page_icon="📌",
    layout="wide",
)
theme.inject_base_css()
painel.render()
