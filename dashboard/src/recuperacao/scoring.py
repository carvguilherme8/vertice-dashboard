"""[B] Motor de scoring determinístico — módulo Recuperação de receita pós-venda.

Regra escrita, sem modelo treinado: não existe histórico rotulado de
tentativas de recuperação (ver v4/09_avaliacao_solucao.md, seção 2.3), então
nenhum peso aqui vem de "o que deu certo antes" — vem de heurística de
negócio declarada em dashboard/config/recuperacao.yaml, auditável e
recalibrável sem tocar em código.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _curva_dias_parado(dias: pd.Series, q_baixo: float, q_mediana: float, q_alto: float) -> pd.Series:
    """Score em [0,1]: sobe até a "janela ótima" (mediana da própria fila) e
    desce depois — pedido recente demais ainda pode se resolver sozinho;
    pedido antigo demais provavelmente já está perdido, mas ainda vale
    tentar com prioridade baixa (nunca zera).
    """
    p10, p50, p90 = dias.quantile([q_baixo, q_mediana, q_alto])
    p10, p50, p90 = float(p10), float(p50), float(p90)

    def _pontuar(d: float) -> float:
        if p50 <= p10 or p90 <= p50:
            return 0.5  # fila degenerada (poucos pontos/quantis colapsados) — score neutro
        if d < p10:
            return 0.5 * d / p10 if p10 > 0 else 0.5
        if d <= p50:
            return 0.5 + 0.5 * (d - p10) / (p50 - p10)
        if d <= p90:
            return 1.0 - 0.5 * (d - p50) / (p90 - p50)
        excedente = (d - p90) / (p90 - p10)
        return max(0.5 - 0.3 * excedente, 0.1)

    return dias.map(_pontuar)


def pontuar(fila: pd.DataFrame, cfg_scoring: dict) -> pd.DataFrame:
    out = fila.copy()
    if out.empty:
        out["score_valor"] = out["score_dias"] = out["score_forma"] = out["score"] = pd.Series(dtype=float)
        return out

    out["score_valor"] = out["receita_liquida"].rank(pct=True)
    out["score_dias"] = _curva_dias_parado(
        out["dias_parado"], cfg_scoring["quantil_baixo"], cfg_scoring["quantil_mediana"], cfg_scoring["quantil_alto"]
    )
    forma_map = cfg_scoring["forma_pagamento"]
    out["score_forma"] = out["metodo_pagamento"].map(forma_map).fillna(np.mean(list(forma_map.values())))

    canal_mult = cfg_scoring.get("canal_multiplicador") or {}
    multiplicador = out["canal"].map(canal_mult).fillna(1.0)

    out["score"] = (
        cfg_scoring["peso_valor"] * out["score_valor"]
        + cfg_scoring["peso_dias_parado"] * out["score_dias"]
        + cfg_scoring["peso_forma_pagamento"] * out["score_forma"]
    ) * multiplicador

    return out.sort_values("score", ascending=False).reset_index(drop=True)
