"""Testes de [A] — pipeline de ingestão. Sem dado novo chegando (o data room
é um snapshot estático), a validação usa `data_referencia` parametrizada em
vez de `datetime.now()` — ver solucao_final/src/recuperacao/ingestao.py.
"""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.recuperacao.ingestao import montar_fila

ROOT = Path(__file__).resolve().parents[1]
VENDAS_PARQUET = ROOT / "data" / "processed" / "vendas.parquet"


def _pedido(order_id, dias_atras, status="Aguardando", ref=date(2024, 1, 26)):
    data_pedido = pd.Timestamp(ref) - pd.Timedelta(days=dias_atras)
    return dict(
        order_id=order_id, customer_id="CLI-0001", data_pedido=data_pedido,
        receita_liquida=100.0, metodo_pagamento="PIX", canal="Instagram Ads", status_pagamento=status,
    )


def test_filtra_apenas_status_elegiveis():
    df = pd.DataFrame([
        _pedido("A", 10, "Aprovado"),
        _pedido("B", 10, "Aguardando"),
        _pedido("C", 10, "Cancelado"),
    ])
    fila = montar_fila(df, date(2024, 1, 26), janela_dias=90)
    assert set(fila["order_id"]) == {"B", "C"}


def test_janela_temporal_inclui_no_limite_exclui_apos():
    df = pd.DataFrame([
        _pedido("NO_LIMITE", 90, "Aguardando"),
        _pedido("FORA", 91, "Aguardando"),
    ])
    fila = montar_fila(df, date(2024, 1, 26), janela_dias=90)
    assert set(fila["order_id"]) == {"NO_LIMITE"}


def test_pedido_futuro_em_relacao_a_data_referencia_e_ignorado():
    df = pd.DataFrame([_pedido("FUTURO", -5, "Aguardando")])  # data_pedido > data_referencia
    fila = montar_fila(df, date(2024, 1, 26), janela_dias=90)
    assert fila.empty


def test_idempotencia():
    df = pd.DataFrame([_pedido("A", 10, "Aguardando"), _pedido("B", 200, "Cancelado")])
    f1 = montar_fila(df, date(2024, 1, 26), janela_dias=90)
    f2 = montar_fila(df, date(2024, 1, 26), janela_dias=90)
    pd.testing.assert_frame_equal(f1, f2)


def test_fila_vazia_quando_nada_elegivel():
    df = pd.DataFrame([_pedido("A", 10, "Aprovado")])
    fila = montar_fila(df, date(2024, 1, 26), janela_dias=90)
    assert fila.empty
    assert list(fila.columns) == [
        "order_id", "customer_id", "data_pedido", "dias_parado",
        "receita_liquida", "metodo_pagamento", "canal", "status_pagamento",
    ]


@pytest.mark.skipif(not VENDAS_PARQUET.exists(), reason="snapshot de dado não disponível")
def test_contagem_bate_com_i02_i03_do_snapshot_real():
    """Regressão contra o dado real, NÃO contra o "6.942/ano" citado na
    proposta. Esse número mistura devolução com I02/I03 (ver notebook 08:
    o freq de M1 usa `pct_pedidos_nao_caixa`, que inclui devolução, embora
    M1 só cubra `inis=['I02','I03']`). A contagem correta de I02+I03 isolados,
    no snapshot inteiro (13 meses), é 3.304 pedidos (1.097 Aguardando +
    2.207 Cancelado) — é esse número que valida a função de ingestão.

    `data_referencia` usa max()+1 dia, não max().date(): a última data do
    snapshot tem 4 pedidos elegíveis com timestamp após 00:00 (ex.: 09:33h),
    e `montar_fila` compara `data_pedido <= data_referencia` — uma
    referência à meia-noite do próprio último dia excluiria esses 4
    pedidos por estarem "no futuro" em relação à meia-noite. Isso não é bug:
    é o comportamento correto de uma rodada que roda no início do dia."""
    vendas = pd.read_parquet(VENDAS_PARQUET)
    ref = vendas["data_pedido"].max().date() + timedelta(days=1)
    fila = montar_fila(vendas, ref, janela_dias=10_000)
    assert len(fila) == 3304
    assert set(fila["status_pagamento"]) == {"Aguardando", "Cancelado"}
