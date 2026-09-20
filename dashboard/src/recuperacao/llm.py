"""Cliente de LLM — usado pelos componentes [D]/[E] (geração de texto) e [F]
(reflexão, com saída JSON). Chamada direta, sem tool use e sem framework de
agente: o LLM só traduz contexto já estruturado em linguagem, nunca decide o
fluxo (ver v4/10_estrutura_solucao.md, componente [C]).

Dois provedores, escolhidos por `cfg["llm"]["provider"]` (recuperacao.yaml):
- "eloagents" — API Sandbox da EloGroup (mesmo endpoint/chave usados na
  Aula07_Pratica.ipynb), via `litellm` para reaproveitar o roteamento já
  validado no notebook em vez de recriar a chamada HTTP na mão.
- "ollama" — modelo local, sem custo e sem dado saindo do ambiente.

Quem chama (`planner.py`, `reflexao.py`) não sabe qual provedor está ativo;
trocar de provedor é mudar o YAML, não o código.
"""
from __future__ import annotations

import os

import litellm
import ollama

try:
    import streamlit as st
except ImportError:  # pragma: no cover — só usado fora do runtime Streamlit em testes
    st = None


class LLMIndisponivel(RuntimeError):
    """Levantado quando o provedor configurado não responde — sinal para a
    UI orientar o operador: rodar `ollama serve`/baixar o modelo (provider
    ollama) ou checar a API key/limite da Sandbox EloAgents (provider
    eloagents)."""


def _api_key_eloagents() -> str:
    # Nunca fica hardcoded no YAML (política versionada em Git): só via
    # secrets do Streamlit (local ou Cloud) ou variável de ambiente.
    if st is not None:
        try:
            chave = st.secrets.get("ELOAGENTS_API_KEY")
        except Exception:
            chave = None
        if chave:
            return chave
    chave = os.environ.get("ELOAGENTS_API_KEY")
    if not chave:
        raise LLMIndisponivel(
            "ELOAGENTS_API_KEY não configurada — defina em "
            "dashboard/.streamlit/secrets.toml (local, veja o .example) ou "
            "nos Secrets do app no Streamlit Cloud (deploy)."
        )
    return chave


def _chat_ollama(prompt: str, model: str, host: str, temperatura: float, formato_json: bool) -> str:
    try:
        resp = ollama.Client(host=host).chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json" if formato_json else None,
            options={"temperature": temperatura},
        )
    except Exception as exc:  # conexão recusada, modelo não baixado, etc.
        raise LLMIndisponivel(f"Falha ao chamar Ollama ({model} @ {host}): {exc}") from exc
    conteudo = resp["message"]["content"]
    return conteudo.strip() if not formato_json else conteudo


def _chat_eloagents(prompt: str, model: str, api_base: str, temperatura: float) -> str:
    """Mesma configuração validada em Aula07_Pratica.ipynb (célula 4): modelo
    com prefixo "openai/" para o LiteLLM tratar como provider OpenAI-HTTP, e
    api_base apontando para a API Sandbox. Sem response_format=json — o
    notebook também não usa modo JSON estrito (célula 22, "CritiqueSchema
    mantido como documentação"); o formato vem só da instrução no prompt,
    e reflexao.py já trata qualquer saída malformada como reprovação."""
    try:
        resp = litellm.completion(
            model=model,
            api_base=api_base,
            api_key=_api_key_eloagents(),
            messages=[{"role": "user", "content": prompt}],
            temperature=temperatura,
        )
    except LLMIndisponivel:
        raise
    except Exception as exc:
        raise LLMIndisponivel(f"Falha ao chamar EloAgents Sandbox ({model}): {exc}") from exc
    return resp["choices"][0]["message"]["content"].strip()


def gerar_texto(prompt: str, cfg_llm: dict) -> str:
    if cfg_llm.get("provider", "ollama") == "eloagents":
        return _chat_eloagents(prompt, cfg_llm["model"], cfg_llm["api_base"], cfg_llm.get("temperatura", 0.2))
    return _chat_ollama(prompt, cfg_llm["model"], cfg_llm["host"], cfg_llm.get("temperatura", 0.2), formato_json=False)


def gerar_json(prompt: str, cfg_llm: dict) -> str:
    if cfg_llm.get("provider", "ollama") == "eloagents":
        return _chat_eloagents(prompt, cfg_llm["model"], cfg_llm["api_base"], cfg_llm.get("temperatura", 0.2))
    return _chat_ollama(prompt, cfg_llm["model"], cfg_llm["host"], cfg_llm.get("temperatura", 0.2), formato_json=True)
