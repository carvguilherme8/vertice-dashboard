"""[H] Registro de execução — log append-only da ação humana sobre cada
pacote. É passivo: registra, não analisa. Sem resultado futuro (o data room
é um snapshot estático, não há como capturar "o cliente pagou depois"), o
ciclo [H]->[B] de recalibração de pesos não é demonstrável dentro do case —
é uma limitação explícita, não um bug (ver v4/09_avaliacao_solucao.md,
seção 5.3).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = ROOT / "data" / "logs" / "execucoes.csv"

COLUNAS = ["timestamp", "order_id", "score", "veredito_justificativa", "veredito_mensagem", "acao_humana"]


def registrar(pacote: dict, acao_humana: str, path: Path = LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    linha = pd.DataFrame([{
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "order_id": pacote["pedido"]["order_id"],
        "score": pacote["pedido"]["score"],
        "veredito_justificativa": pacote["justificativa"]["veredito"],
        "veredito_mensagem": pacote["mensagem"]["veredito"],
        "acao_humana": acao_humana,
    }])
    existe = path.exists()
    linha.to_csv(path, mode="a", header=not existe, index=False, columns=COLUNAS)
