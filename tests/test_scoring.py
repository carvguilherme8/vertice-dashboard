import pandas as pd

from src.recuperacao.scoring import pontuar

CFG = {
    "peso_valor": 0.45,
    "peso_dias_parado": 0.40,
    "peso_forma_pagamento": 0.15,
    "quantil_baixo": 0.10,
    "quantil_mediana": 0.50,
    "quantil_alto": 0.90,
    "forma_pagamento": {"Boleto": 1.00, "PIX": 0.60, "Cartão de Crédito": 0.50, "Vale-Troca": 0.30},
    "canal_multiplicador": {},
}


def _fila(rows):
    base = dict(customer_id="CLI-1", data_pedido=pd.Timestamp("2024-01-01"), canal="Instagram Ads", status_pagamento="Aguardando")
    return pd.DataFrame([{**base, **r} for r in rows])


def test_maior_valor_gera_maior_score_valor():
    fila = _fila([
        dict(order_id="BAIXO", receita_liquida=100.0, dias_parado=100, metodo_pagamento="PIX"),
        dict(order_id="ALTO", receita_liquida=900.0, dias_parado=100, metodo_pagamento="PIX"),
    ])
    out = pontuar(fila, CFG)
    alto = out.set_index("order_id").loc["ALTO", "score_valor"]
    baixo = out.set_index("order_id").loc["BAIXO", "score_valor"]
    assert alto > baixo


def test_forma_pagamento_influencia_score():
    fila = _fila([
        dict(order_id="BOLETO", receita_liquida=500.0, dias_parado=100, metodo_pagamento="Boleto"),
        dict(order_id="VALE", receita_liquida=500.0, dias_parado=100, metodo_pagamento="Vale-Troca"),
    ])
    out = pontuar(fila, CFG)
    boleto = out.set_index("order_id").loc["BOLETO", "score"]
    vale = out.set_index("order_id").loc["VALE", "score"]
    assert boleto > vale


def test_fila_vazia_nao_quebra():
    fila = pd.DataFrame(columns=["order_id", "receita_liquida", "dias_parado", "metodo_pagamento", "canal"])
    out = pontuar(fila, CFG)
    assert out.empty
    assert "score" in out.columns


def test_ordenado_por_score_decrescente():
    fila = _fila([
        dict(order_id="A", receita_liquida=100.0, dias_parado=50, metodo_pagamento="PIX"),
        dict(order_id="B", receita_liquida=900.0, dias_parado=150, metodo_pagamento="Boleto"),
        dict(order_id="C", receita_liquida=300.0, dias_parado=300, metodo_pagamento="Vale-Troca"),
    ])
    out = pontuar(fila, CFG)
    assert list(out["score"]) == sorted(out["score"], reverse=True)
