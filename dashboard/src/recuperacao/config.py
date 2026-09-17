"""[J] Arquivo de configuração e políticas — carregamento com cache.

Mesmo padrão de src/data.py: uma função cacheada que devolve um dict; quem
chama nunca lê o YAML diretamente.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "dashboard" / "config" / "recuperacao.yaml"


@st.cache_data(show_spinner=False)
def carregar_config(path: str | Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
