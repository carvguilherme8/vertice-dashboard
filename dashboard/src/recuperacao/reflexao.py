"""[F] Camada de reflexão — crítico com rubrica, passe único.

Valida um artefato (justificativa ou mensagem) contra o contexto que o
gerou. Se o JSON vier malformado, trata como reprovação (fail-closed): o
pedido segue para revisão humana intensa em vez de ser aprovado por
default — é o comportamento seguro descrito em v4/10_estrutura_solucao.md,
componente [F].
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from . import llm

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "reflexao.md"


class Veredito(BaseModel):
    veredito: Literal["aprovado", "ressalva", "rejeitado"]
    motivo: str


def avaliar(texto: str, contexto: dict, cfg_llm: dict) -> Veredito:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.format(contexto_json=json.dumps(contexto, ensure_ascii=False, default=str), texto=texto)

    try:
        bruto = llm.gerar_json(prompt, cfg_llm["model"], cfg_llm["host"], cfg_llm.get("temperatura", 0.2))
        return Veredito.model_validate_json(bruto)
    except (json.JSONDecodeError, ValidationError, llm.OllamaIndisponivel) as exc:
        return Veredito(veredito="rejeitado", motivo=f"reflexão indisponível ou saída inválida: {exc}")
