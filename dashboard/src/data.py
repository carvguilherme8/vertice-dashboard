"""Carregamento e cache das bases processadas do case Vértice."""
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"


@st.cache_data(show_spinner="Carregando bases...")
def load_all() -> dict[str, pd.DataFrame]:
    vendas = pd.read_parquet(DATA_DIR / "vendas.parquet")
    clientes = pd.read_parquet(DATA_DIR / "clientes.parquet")
    estoque = pd.read_parquet(DATA_DIR / "estoque.parquet")
    atendimento = pd.read_parquet(DATA_DIR / "atendimento.parquet")
    marketing = pd.read_parquet(DATA_DIR / "marketing.parquet")
    return {
        "vendas": vendas,
        "clientes": clientes,
        "estoque": estoque,
        "atendimento": atendimento,
        "marketing": marketing,
    }


def filtrar_vendas(vendas: pd.DataFrame, data_ini, data_fim, canais: list[str]) -> pd.DataFrame:
    # data_fim é uma data (sem hora) — comparar com "<=" truncaria pra meia-noite
    # do último dia e descartaria todo pedido feito depois das 00:00 nesse dia
    # (era o caso dos 28 pedidos de 26/01/2024, o último dia da base: sumiam do
    # filtro padrão "período inteiro" sem nenhum aviso). "<" do dia seguinte
    # inclui o dia inteiro, não importa a hora do pedido.
    fim_exclusivo = pd.Timestamp(data_fim) + pd.Timedelta(days=1)
    out = vendas[(vendas["data_pedido"] >= pd.Timestamp(data_ini)) & (vendas["data_pedido"] < fim_exclusivo)]
    if canais:
        out = out[out["canal"].isin(canais)]
    return out
