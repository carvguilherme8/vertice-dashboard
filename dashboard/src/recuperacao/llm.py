"""Cliente Ollama — usado pelos componentes [D]/[E] (geração de texto) e [F]
(reflexão, com saída JSON). Chamada direta, sem tool use e sem framework de
agente: o LLM só traduz contexto já estruturado em linguagem, nunca decide o
fluxo (ver v4/10_estrutura_solucao.md, componente [C]).
"""
from __future__ import annotations

import ollama


class OllamaIndisponivel(RuntimeError):
    """Levantado quando o servidor Ollama não responde — sinal para a UI
    orientar o operador a rodar `ollama serve` / `ollama pull <modelo>`."""


def _client(host: str) -> ollama.Client:
    return ollama.Client(host=host)


def gerar_texto(prompt: str, model: str, host: str, temperatura: float = 0.2) -> str:
    try:
        resp = _client(host).chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperatura},
        )
    except Exception as exc:  # conexão recusada, modelo não baixado, etc.
        raise OllamaIndisponivel(f"Falha ao chamar Ollama ({model} @ {host}): {exc}") from exc
    return resp["message"]["content"].strip()


def gerar_json(prompt: str, model: str, host: str, temperatura: float = 0.2) -> str:
    """Mesma chamada, mas em modo JSON — o parse/validação (pydantic) fica em
    reflexao.py, não aqui: este módulo só fala com o Ollama."""
    try:
        resp = _client(host).chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": temperatura},
        )
    except Exception as exc:
        raise OllamaIndisponivel(f"Falha ao chamar Ollama ({model} @ {host}): {exc}") from exc
    return resp["message"]["content"]
