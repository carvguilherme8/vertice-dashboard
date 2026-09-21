"""[A] Pipeline de ingestão da fila — módulo Recuperação de receita pós-venda.

Lê Vendas e devolve, para uma rodada, o conjunto de pedidos elegíveis (I02 —
pagamento aguardando; I03 — cancelado no pagamento) dentro da janela temporal
configurada. É uma função pura: recebe a "data de hoje" como parâmetro
(`data_referencia`) em vez de chamar datetime.now() internamente — é isso que
permite testar e simular rodadas passadas sobre o mesmo snapshot estático de
dado, sem depender de dado novo chegar (ver tests/test_ingestao.py e
scripts/backtest_rodadas.py).
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

STATUS_ELEGIVEIS = ("Aguardando", "Cancelado")

COLUNAS_FILA = [
    "order_id", "customer_id", "data_pedido", "dias_parado",
    "receita_liquida", "metodo_pagamento", "canal", "status_pagamento",
]


def montar_fila(vendas: pd.DataFrame, data_referencia: date | datetime, janela_dias: int) -> pd.DataFrame:
    ref = pd.Timestamp(data_referencia)
    elegiveis = vendas[
        vendas["status_pagamento"].isin(STATUS_ELEGIVEIS) & (vendas["data_pedido"] <= ref)
    ].copy()
    elegiveis["dias_parado"] = (ref - elegiveis["data_pedido"]).dt.days
    fila = elegiveis[elegiveis["dias_parado"] <= janela_dias]
    return fila[COLUNAS_FILA].reset_index(drop=True)
