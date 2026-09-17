"""Replay de datas históricas como "rodadas" sobre o snapshot estático de
Vendas — prova que o pipeline de ingestão + scoring funciona rodada a
rodada sem depender de dado novo chegar (o data room não recebe atualização).

Uso:
    python scripts/backtest_rodadas.py --inicio 2023-06-01 --fim 2024-01-26 --step 7

Não chama o Ollama — só exercita [A] e [B] (determinísticos, sem LLM), que é
o suficiente para validar volume e composição da fila por rodada.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"
sys.path.insert(0, str(DASHBOARD_DIR))

import pandas as pd  # noqa: E402

from src.recuperacao.config import carregar_config  # noqa: E402
from src.recuperacao.ingestao import montar_fila  # noqa: E402
from src.recuperacao.scoring import pontuar  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VENDAS_PARQUET = ROOT / "data" / "processed" / "vendas.parquet"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", required=True, help="YYYY-MM-DD")
    ap.add_argument("--fim", required=True, help="YYYY-MM-DD")
    ap.add_argument("--step", type=int, default=7, help="passo em dias entre rodadas simuladas")
    ap.add_argument("--saida", default=str(ROOT / "data" / "logs" / "backtest_rodadas.csv"))
    args = ap.parse_args()

    vendas = pd.read_parquet(VENDAS_PARQUET)
    cfg = carregar_config()

    inicio, fim = date.fromisoformat(args.inicio), date.fromisoformat(args.fim)
    linhas = []
    d = inicio
    while d <= fim:
        fila = montar_fila(vendas, d, cfg["ingestao"]["janela_dias"])
        fila_scored = pontuar(fila, cfg["scoring"])
        linhas.append({
            "data_referencia": d.isoformat(),
            "tamanho_fila": len(fila),
            "n_aguardando": int((fila["status_pagamento"] == "Aguardando").sum()) if not fila.empty else 0,
            "n_cancelado": int((fila["status_pagamento"] == "Cancelado").sum()) if not fila.empty else 0,
            "receita_liquida_na_fila": float(fila["receita_liquida"].sum()) if not fila.empty else 0.0,
            "score_medio_top_n": float(fila_scored.head(cfg["fila"]["top_n"])["score"].mean()) if not fila_scored.empty else None,
        })
        d += timedelta(days=args.step)

    out = pd.DataFrame(linhas)
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.saida, index=False)
    print(out.to_string(index=False))
    print(f"\nSalvo em {args.saida} — {len(out)} rodadas simuladas sobre o snapshot estático.")


if __name__ == "__main__":
    main()
