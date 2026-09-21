"""[C] Planner — orquestrador de etapas do módulo Recuperação de receita
pós-venda. Máquina de estados fixa, escrita por humanos: o LLM nunca decide
o próximo passo, só é chamado dentro de etapas específicas (justificativa,
mensagem, reflexão). Ver v4/10_estrutura_solucao.md, componente [C].
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import ingestao, reflexao, scoring
from .llm import LLMIndisponivel, gerar_texto

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

SITUACAO_TEXTO = {
    "Aguardando": "pagamento ainda não confirmado",
    "Cancelado": "pagamento cancelado antes da confirmação",
}
INSTRUCAO_SITUACAO = {
    "Aguardando": "Envie um lembrete cordial de que o pagamento está pendente e ofereça ajuda caso o cliente tenha tido dificuldade para concluir o pagamento.",
    "Cancelado": "Convide o cliente a retomar o pedido, oferecendo ajuda para tentar novamente com outro meio de pagamento, sem pressão.",
}


def _num_br(v: float, decimals: int = 2) -> str:
    s = f"{v:,.{decimals}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def _montar_contexto(pedido: pd.Series) -> dict:
    return {
        "order_id": pedido["order_id"],
        "status_pagamento": pedido["status_pagamento"],
        "receita_liquida": round(float(pedido["receita_liquida"]), 2),
        "dias_parado": int(pedido["dias_parado"]),
        "metodo_pagamento": pedido["metodo_pagamento"],
        "canal": pedido["canal"],
        "score": round(float(pedido["score"]), 3),
        "score_valor": round(float(pedido["score_valor"]), 3),
        "score_dias": round(float(pedido["score_dias"]), 3),
        "score_forma": round(float(pedido["score_forma"]), 3),
    }


def _gerar_justificativa(contexto: dict, cfg_llm: dict) -> str:
    template = (PROMPTS_DIR / "justificativa.md").read_text(encoding="utf-8")
    campos = {**contexto, "receita_liquida": _num_br(contexto["receita_liquida"])}
    prompt = template.format(**campos)
    return gerar_texto(prompt, cfg_llm)


def _gerar_mensagem(contexto: dict, cfg_politica: dict, cfg_llm: dict) -> str:
    template = (PROMPTS_DIR / "mensagem_cliente.md").read_text(encoding="utf-8")
    status = contexto["status_pagamento"]
    campos = {
        **contexto,
        "receita_liquida": _num_br(contexto["receita_liquida"]),
        "teto_desconto_pct": cfg_politica["teto_desconto_pct"],
        "tom_canal": cfg_politica["tom_por_canal"].get(contexto["canal"], cfg_politica["tom_por_canal"]["default"]),
        "situacao_texto": SITUACAO_TEXTO.get(status, status),
        "instrucao_situacao": INSTRUCAO_SITUACAO.get(status, ""),
    }
    prompt = template.format(**campos)
    return gerar_texto(prompt, cfg_llm)


def _contexto_para_reflexao(contexto: dict) -> dict:
    """A reflexão compara o texto gerado, que cita valores no formato BR
    ("R$ 1.574,34"), contra o contexto — se o contexto trouxer o float bruto
    (1574.34), um modelo pequeno pode não reconhecer que é o mesmo número e
    reprovar por falso positivo. Formatar aqui do mesmo jeito elimina isso."""
    return {**contexto, "receita_liquida": _num_br(contexto["receita_liquida"])}


def _com_reflexao(gerar_fn, contexto: dict, cfg: dict, max_regeneracoes: int, rotulo: str = "", on_progress=None) -> dict:
    def _avisar(msg: str) -> None:
        if on_progress:
            on_progress(f"{contexto['order_id']} · {rotulo}: {msg}" if rotulo else f"{contexto['order_id']}: {msg}")

    contexto_reflexao = _contexto_para_reflexao(contexto)
    _avisar("gerando...")
    texto = gerar_fn(contexto, cfg)
    veredito = reflexao.avaliar(texto, contexto_reflexao, cfg["llm"])
    _avisar(f"reflexão → {veredito.veredito} ({veredito.motivo})")
    tentativas = 0
    while veredito.veredito == "rejeitado" and tentativas < max_regeneracoes:
        _avisar("reprovado, regenerando...")
        texto = gerar_fn(contexto, cfg)
        veredito = reflexao.avaliar(texto, contexto_reflexao, cfg["llm"])
        tentativas += 1
        _avisar(f"reflexão (regeneração {tentativas}) → {veredito.veredito} ({veredito.motivo})")
    revisao_humana_intensa = veredito.veredito == "rejeitado" and tentativas >= max_regeneracoes
    return {"texto": texto, "veredito": veredito.veredito, "motivo": veredito.motivo, "revisao_humana_intensa": revisao_humana_intensa}


def executar_rodada(vendas: pd.DataFrame, data_referencia, cfg: dict, top_n: int | None = None, on_progress=None) -> list[dict]:
    """Sequência fixa: ingestão -> scoring -> top-N -> por pedido: contexto ->
    justificativa -> mensagem -> reflexão (com regeneração condicional).

    `top_n` sobrepõe cfg["fila"]["top_n"] só nesta execução (ex.: um seletor
    na UI para testar com poucos pedidos sem editar a política em YAML) — não
    pode passar do teto declarado na política, só reduzir.
    `on_progress(str)`, se passado, recebe uma linha de log por evento (chamada
    ao LLM, veredito da reflexão) — usado pela UI para mostrar progresso ao
    vivo; o planner continua puro/testável sem Streamlit quando omitido."""
    teto = cfg["fila"]["top_n"]
    n = min(top_n, teto) if top_n is not None else teto

    fila = ingestao.montar_fila(vendas, data_referencia, cfg["ingestao"]["janela_dias"])
    fila = scoring.pontuar(fila, cfg["scoring"])
    top_n_fila = fila.head(n)

    pacotes = []
    for _, pedido in top_n_fila.iterrows():
        contexto = _montar_contexto(pedido)
        if on_progress:
            on_progress(f"{contexto['order_id']}: iniciando (score {contexto['score']:.2f})")
        try:
            just = _com_reflexao(
                lambda ctx, c: _gerar_justificativa(ctx, c["llm"]), contexto, cfg, cfg["reflexao"]["max_regeneracoes"],
                rotulo="justificativa", on_progress=on_progress,
            )
            msg = _com_reflexao(
                lambda ctx, c: _gerar_mensagem(ctx, c["politica"], c["llm"]), contexto, cfg, cfg["reflexao"]["max_regeneracoes"],
                rotulo="mensagem", on_progress=on_progress,
            )
            erro = None
        except LLMIndisponivel as exc:
            just = msg = {"texto": "", "veredito": "rejeitado", "motivo": str(exc), "revisao_humana_intensa": True}
            erro = str(exc)
            if on_progress:
                on_progress(f"{contexto['order_id']}: LLM indisponível — {exc}")

        pacotes.append({"pedido": contexto, "justificativa": just, "mensagem": msg, "erro": erro})

    return pacotes
