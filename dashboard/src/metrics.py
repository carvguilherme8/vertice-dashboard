"""Cálculos determinísticos que sustentam o Painel Único de Decisão Comercial.

Cada função reproduz uma fórmula documentada em outputs/metodologia_impacto.md
e outputs/sintese_hipoteses.md. Nada aqui é estimado "no olho": todo número
sai de uma coluna específica das bases em data/processed.
"""
from __future__ import annotations

import pandas as pd

CANAL_ONDE_PEDIDO_FORA_CHATBOT_CUSTO = 2.00  # R$/ticket, custo médio observado do ChatBot


def margem_mensal(vendas: pd.DataFrame) -> pd.DataFrame:
    v = vendas.copy()
    v["mes"] = v["data_pedido"].values.astype("datetime64[M]")
    realizado_mask = (~v["devolvido"]) & (v["status_pagamento"] == "Aprovado")
    g_contabil = v.groupby("mes")["receita_liquida"].sum().rename("receita_liquida")
    g_margem_contabil = v.groupby("mes")["margem_contribuicao"].sum().rename("margem_contabil")
    g_margem_realizada = v[realizado_mask].groupby("mes")["margem_contribuicao"].sum().rename("margem_realizada")
    g_desconto = v.groupby("mes")["desconto_reais"].sum().rename("desconto_reais")
    g_pedidos = v.groupby("mes")["order_id"].count().rename("pedidos")
    out = pd.concat([g_contabil, g_margem_contabil, g_margem_realizada, g_desconto, g_pedidos], axis=1).fillna(0.0).reset_index()
    out["margem_pct_realizada"] = out["margem_realizada"] / out["receita_liquida"]
    return out.sort_values("mes")


def atendimento_por_categoria(atendimento: pd.DataFrame) -> pd.DataFrame:
    g = (
        atendimento.groupby("categoria_problema")
        .agg(tickets=("ticket_id", "count"), custo_total=("custo_operacional_ticket", "sum"), csat_medio=("nota_csat", "mean"))
        .reset_index()
        .sort_values("tickets", ascending=False)
    )
    return g


def atendimento_por_canal(atendimento: pd.DataFrame) -> pd.DataFrame:
    g = (
        atendimento.groupby("canal_entrada")
        .agg(tickets=("ticket_id", "count"), custo_medio=("custo_operacional_ticket", "mean"))
        .reset_index()
        .sort_values("tickets", ascending=False)
    )
    return g


# ---------------------------------------------------------------- margem ----
def margem_realizada(vendas: pd.DataFrame) -> dict:
    contabil = float(vendas["margem_contribuicao"].sum())
    realizado_mask = (~vendas["devolvido"]) & (vendas["status_pagamento"] == "Aprovado")
    realizado = float(vendas.loc[realizado_mask, "margem_contribuicao"].sum())
    receita_liq = float(vendas["receita_liquida"].sum())
    return {
        "contabil": contabil,
        "realizado": realizado,
        "gap": contabil - realizado,
        "pct_contabil": contabil / receita_liq if receita_liq else 0.0,
        "pct_realizado": realizado / receita_liq if receita_liq else 0.0,
        "n_devolvidos": int(vendas["devolvido"].sum()),
        "n_nao_aprovados": int((vendas["status_pagamento"] != "Aprovado").sum()),
    }


# --------------------------------------------------------------- desconto ---
FAIXAS_DESCONTO = [-0.001, 0, 0.10, 0.20, 0.25, 0.30, 1.0]
LABELS_DESCONTO = ["0%", "1-10%", "11-20%", "21-25%", "26-30%", "30%+"]


def desconto_geral(vendas: pd.DataFrame) -> dict:
    total = float(vendas["desconto_reais"].sum())
    receita_bruta = float(vendas["receita_bruta"].sum())
    return {
        "total": total,
        "pct_receita_bruta": total / receita_bruta if receita_bruta else 0.0,
        "pct_pedidos_com_desconto": float((vendas["desconto_reais"] > 0).mean()),
    }


def desconto_por_faixa(vendas: pd.DataFrame) -> pd.DataFrame:
    v = vendas.copy()
    v["faixa_desconto"] = pd.cut(v["desconto_pct"], bins=FAIXAS_DESCONTO, labels=LABELS_DESCONTO)
    g = (
        v.groupby("faixa_desconto", observed=True)
        .agg(
            pedidos=("order_id", "count"),
            desconto_total=("desconto_reais", "sum"),
            margem_pct_media=("margem_pct", "mean"),
            receita_liquida=("receita_liquida", "sum"),
        )
        .reset_index()
    )
    return g


def simular_teto_desconto(vendas: pd.DataFrame, teto_pct: float) -> dict:
    teto = teto_pct / 100
    acima = vendas[vendas["desconto_pct"] > teto]
    dentro = vendas[vendas["desconto_pct"] <= teto]
    return {
        "teto_pct": teto_pct,
        "n_pedidos_acima": int(len(acima)),
        "pct_pedidos_acima": len(acima) / len(vendas) if len(vendas) else 0.0,
        "desconto_concedido_acima": float(acima["desconto_reais"].sum()),
        "margem_pct_acima": float(acima["margem_pct"].mean()) if len(acima) else None,
        "margem_pct_dentro": float(dentro["margem_pct"].mean()) if len(dentro) else None,
    }


# ---------------------------------------------------------------- estoque ---
def curva_abc(vendas: pd.DataFrame, estoque: pd.DataFrame) -> pd.DataFrame:
    receita_sku = vendas.groupby("sku_id")["receita_liquida"].sum().sort_values(ascending=False)
    total = receita_sku.sum()
    cum_pct = receita_sku.cumsum() / total if total else receita_sku.cumsum()
    curva = pd.cut(cum_pct, bins=[-0.001, 0.80, 0.95, 1.0], labels=["A", "B", "C"])
    df_curva = pd.DataFrame(
        {"sku_id": receita_sku.index, "receita_liquida_periodo": receita_sku.values, "cum_pct_receita": cum_pct.values, "curva": curva.values}
    )
    merged = estoque.merge(df_curva, on="sku_id", how="left")
    merged["curva"] = merged["curva"].astype(object).fillna("C")
    merged["receita_liquida_periodo"] = merged["receita_liquida_periodo"].fillna(0.0)
    merged["critico"] = merged["ruptura"] | merged["abaixo_ponto_pedido"]
    return merged


def skus_criticos_curva_a(merged: pd.DataFrame, vendas: pd.DataFrame) -> dict:
    curva_a = merged[merged["curva"] == "A"]
    criticos = curva_a[curva_a["critico"]]
    dias_janela = (vendas["data_pedido"].max() - vendas["data_pedido"].min()).days + 1
    receita_criticos = float(criticos["receita_liquida_periodo"].sum())
    receita_dia = receita_criticos / dias_janela if dias_janela else 0.0
    return {
        "n_criticos": int(len(criticos)),
        "total_curva_a": int(len(curva_a)),
        "pct_da_curva_a": len(criticos) / len(curva_a) if len(curva_a) else 0.0,
        "receita_dia_risco": receita_dia,
        "receita_em_risco_anual": receita_dia * 365,
        "tabela": criticos.sort_values("receita_liquida_periodo", ascending=False),
    }


def skus_criticos_por_categoria(merged: pd.DataFrame) -> pd.DataFrame:
    """Onde priorizar reposição primeiro: SKUs da curva A (80% da receita) que
    também estão em ruptura ou abaixo do ponto de pedido, por categoria."""
    criticos = merged[(merged["curva"] == "A") & merged["critico"]]
    return (
        criticos.groupby("categoria").size().rename("n_criticos").reset_index().sort_values("n_criticos", ascending=False)
    )


def estoque_parado(estoque: pd.DataFrame) -> dict:
    hoje = pd.Timestamp.today()
    dias_parado = (hoje - estoque["data_ultima_entrada"]).dt.days
    parado_2anos = dias_parado > 730
    return {
        "pct_parado_2anos": float(parado_2anos.mean()),
        "n_parado_2anos": int(parado_2anos.sum()),
    }


def estoque_parado_por_categoria(estoque: pd.DataFrame) -> pd.DataFrame:
    e = estoque.copy()
    hoje = pd.Timestamp.today()
    e["parado_2anos"] = (hoje - e["data_ultima_entrada"]).dt.days > 730
    return e.groupby("categoria")["parado_2anos"].mean().rename("pct_parado_2anos").reset_index().sort_values("pct_parado_2anos", ascending=False)


# --------------------------------------------------------------- canais -----
def gap_marketplace(vendas: pd.DataFrame) -> dict:
    g = (
        vendas.groupby("canal")
        .agg(receita_liquida=("receita_liquida", "sum"), margem=("margem_contribuicao", "sum"), frete=("custo_frete", "sum"))
        .reset_index()
    )
    g["margem_pct"] = g["margem"] / g["receita_liquida"]
    g["frete_pct"] = g["frete"] / g["receita_liquida"]

    if "Marketplace" not in g["canal"].values:
        return {"tabela": g}

    mp = g[g["canal"] == "Marketplace"].iloc[0]
    outros = g[g["canal"] != "Marketplace"]
    outros_margem_pct = outros["margem"].sum() / outros["receita_liquida"].sum()
    outros_frete_pct = outros["frete"].sum() / outros["receita_liquida"].sum()

    gap_margem_pp = outros_margem_pct - mp["margem_pct"]
    gap_frete_pp = mp["frete_pct"] - outros_frete_pct

    return {
        "tabela": g,
        "margem_pct_marketplace": float(mp["margem_pct"]),
        "margem_pct_outros": float(outros_margem_pct),
        "gap_margem_pp": float(gap_margem_pp),
        "gap_margem_r": float(gap_margem_pp * mp["receita_liquida"]),
        "frete_pct_marketplace": float(mp["frete_pct"]),
        "frete_pct_outros": float(outros_frete_pct),
        "gap_frete_pp": float(gap_frete_pp),
        "gap_frete_r": float(gap_frete_pp * mp["receita_liquida"]),
        "receita_marketplace": float(mp["receita_liquida"]),
    }


def margem_por_categoria(vendas: pd.DataFrame) -> pd.DataFrame:
    g = (
        vendas.groupby("categoria")
        .agg(receita_liquida=("receita_liquida", "sum"), margem=("margem_contribuicao", "sum"))
        .reset_index()
    )
    g["margem_pct"] = g["margem"] / g["receita_liquida"]
    return g.sort_values("margem_pct")


def cmv_estabilidade(vendas: pd.DataFrame) -> dict:
    geral = vendas["custo_produto"].sum() / vendas["receita_bruta"].sum()
    g = vendas.groupby("categoria")[["custo_produto", "receita_bruta"]].sum()
    por_categoria = g["custo_produto"] / g["receita_bruta"]
    return {"geral": float(geral), "por_categoria": por_categoria, "amplitude_pp": float(por_categoria.max() - por_categoria.min())}


# ------------------------------------------------------------- devolução ----
# Módulo "Prevenção de devolução na origem" (I04 + I08). Causa operacional —
# defeito, tamanho errado, atraso — é endereçável por ação da empresa;
# arrependimento e "não gostei" não são (o cliente decide, não um processo
# que a Vértice controla). Ver v4/proposta_solucao_vertice_v4.html, iniciativa
# I04: "não se elimina 100% da devolução — arrependimento e 'não gostei'
# ficam fora".
MOTIVOS_ENDERECAVEIS = ("Produto com defeito", "Tamanho errado", "Atraso na entrega")


def devolucao_geral(vendas: pd.DataFrame) -> dict:
    dev = vendas[vendas["devolvido"]]
    enderecavel = dev[dev["motivo_devolucao"].isin(MOTIVOS_ENDERECAVEIS)]
    return {
        "n_devolvidos": int(len(dev)),
        "pct_pedidos": float(len(dev) / len(vendas)) if len(vendas) else 0.0,
        "margem_perdida_total": float(dev["margem_contribuicao"].sum()),
        "margem_perdida_enderecavel": float(enderecavel["margem_contribuicao"].sum()),
        "margem_perdida_nao_enderecavel": float(dev.loc[~dev.index.isin(enderecavel.index), "margem_contribuicao"].sum()),
    }


def devolucao_por_canal(vendas: pd.DataFrame) -> pd.DataFrame:
    g = vendas.groupby("canal").agg(pedidos=("order_id", "count"), devolvidos=("devolvido", "sum")).reset_index()
    g["taxa_devolucao"] = g["devolvidos"] / g["pedidos"]
    return g.sort_values("taxa_devolucao", ascending=False)


def devolucao_por_motivo(vendas: pd.DataFrame) -> pd.DataFrame:
    dev = vendas[vendas["devolvido"]]
    g = (
        dev.groupby("motivo_devolucao")
        .agg(pedidos=("order_id", "count"), margem_perdida=("margem_contribuicao", "sum"))
        .reset_index()
    )
    g["enderecavel"] = g["motivo_devolucao"].isin(MOTIVOS_ENDERECAVEIS)
    return g.sort_values("margem_perdida", ascending=False)


def devolucao_por_fornecedor(vendas: pd.DataFrame, estoque: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """Só causas endereçáveis — arrependimento/'não gostei' não é problema
    de fornecedor, é decisão do cliente."""
    dev = vendas[vendas["devolvido"] & vendas["motivo_devolucao"].isin(MOTIVOS_ENDERECAVEIS)]
    j = dev.merge(estoque[["sku_id", "fornecedor_id"]], on="sku_id", how="left")
    g = (
        j.groupby("fornecedor_id")
        .agg(pedidos=("order_id", "count"), margem_perdida=("margem_contribuicao", "sum"))
        .reset_index()
        .sort_values("margem_perdida", ascending=False)
    )
    return g.head(top_n)


def devolucao_por_sku(vendas: pd.DataFrame, estoque: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    dev = vendas[vendas["devolvido"] & vendas["motivo_devolucao"].isin(MOTIVOS_ENDERECAVEIS)]
    j = dev.merge(estoque[["sku_id", "nome_produto", "fornecedor_id"]], on="sku_id", how="left")
    g = (
        j.groupby(["sku_id", "nome_produto", "fornecedor_id"])
        .agg(pedidos=("order_id", "count"), margem_perdida=("margem_contribuicao", "sum"), motivo_mais_comum=("motivo_devolucao", lambda s: s.mode().iat[0]))
        .reset_index()
        .sort_values("margem_perdida", ascending=False)
    )
    return g.head(top_n)


# ------------------------------------------------------------ atendimento ---
def chatbot_economia(atendimento: pd.DataFrame) -> dict:
    onde_pedido = atendimento[atendimento["categoria_problema"] == "Onde está meu pedido?"]
    fora_chatbot = onde_pedido[onde_pedido["canal_entrada"] != "ChatBot"]

    n = len(fora_chatbot)
    custo_atual = float(fora_chatbot["custo_operacional_ticket"].sum())
    custo_se_chatbot = n * CANAL_ONDE_PEDIDO_FORA_CHATBOT_CUSTO
    economia_total = custo_atual - custo_se_chatbot

    dias_janela = (atendimento["data_abertura"].max() - atendimento["data_abertura"].min()).days
    anos_janela = dias_janela / 365 if dias_janela else 1.0
    economia_anual = economia_total / anos_janela

    is_chatbot = atendimento["canal_entrada"] == "ChatBot"
    resolvido = atendimento["status_atendimento"] == "Resolvido"

    return {
        "n_tickets_migraveis": n,
        "custo_atual_janela": custo_atual,
        "custo_se_chatbot_janela": custo_se_chatbot,
        "economia_total_janela": economia_total,
        "anos_janela": anos_janela,
        "economia_anual": economia_anual,
        "csat_chatbot": float(atendimento.loc[is_chatbot, "nota_csat"].mean()),
        "csat_humano": float(atendimento.loc[~is_chatbot, "nota_csat"].mean()),
        "resolucao_chatbot": float(resolvido[is_chatbot].mean()),
        "resolucao_humano": float(resolvido[~is_chatbot].mean()),
        "custo_medio_chatbot": float(atendimento.loc[is_chatbot, "custo_operacional_ticket"].mean()),
        "custo_medio_humano": float(atendimento.loc[~is_chatbot, "custo_operacional_ticket"].mean()),
    }


def volume_falha_operacional(atendimento: pd.DataFrame) -> dict:
    falha = atendimento["categoria_problema"].isin(["Onde está meu pedido?", "Defeito", "Pagamento não aprovado"])
    return {
        "pct_tickets_falha": float(falha.mean()),
        "pct_custo_falha": float(atendimento.loc[falha, "custo_operacional_ticket"].sum() / atendimento["custo_operacional_ticket"].sum()),
    }


# ------------------------------------------------------------- marketing ----
def integridade_marketing(vendas: pd.DataFrame, marketing: pd.DataFrame) -> dict:
    receita_marketing = float(marketing["receita_gerada"].sum())
    receita_vendas = float(vendas["receita_bruta"].sum())
    conv_marketing = float(marketing["conversoes"].sum())
    n_pedidos = len(vendas)
    return {
        "receita_declarada_marketing": receita_marketing,
        "receita_real_vendas": receita_vendas,
        "multiplicador_receita": receita_marketing / receita_vendas if receita_vendas else float("nan"),
        "conversoes_declaradas": conv_marketing,
        "pedidos_reais": n_pedidos,
        "multiplicador_conversoes": conv_marketing / n_pedidos if n_pedidos else float("nan"),
    }


# ------------------------------------------------------------- clientes -----
# clientes.parquet é usado como cadastro autocontido — vendas.customer_id não
# identifica cliente de forma confiável (1 ID concentra 40,6% dos pedidos; ver
# notebooks drive/01_qualidade_dados.ipynb, seção 5), então estes números NUNCA
# cruzam com vendas.csv, só resumem a base de clientes isoladamente.
SEGMENTOS_RISCO = ("Em Risco", "Churn", "Hibernando")


def clientes_kpis(clientes: pd.DataFrame) -> dict:
    em_risco = clientes["segmento_rfm"].isin(SEGMENTOS_RISCO)
    return {
        "n_clientes": int(len(clientes)),
        "ltv_medio": float(clientes["ltv_acumulado"].mean()),
        "ltv_total": float(clientes["ltv_acumulado"].sum()),
        "pct_em_risco": float(em_risco.mean()),
        "ltv_em_risco": float(clientes.loc[em_risco, "ltv_acumulado"].sum()),
    }


def clientes_por_segmento(clientes: pd.DataFrame) -> pd.DataFrame:
    g = (
        clientes.groupby("segmento_rfm")
        .agg(n_clientes=("customer_id", "count"), ltv_total=("ltv_acumulado", "sum"), ltv_medio=("ltv_acumulado", "mean"))
        .reset_index()
        .sort_values("ltv_total", ascending=False)
    )
    return g


FIDELIDADE_ORDEM = ["Bronze", "Silver", "Gold", "Platinum"]


def clientes_por_fidelidade(clientes: pd.DataFrame) -> pd.DataFrame:
    g = (
        clientes.groupby("nivel_fidelidade")
        .agg(n_clientes=("customer_id", "count"), ltv_medio=("ltv_acumulado", "mean"))
        .reindex(FIDELIDADE_ORDEM)
        .reset_index()
    )
    return g


# ------------------------------------------------------- guardrail (regra) --
def guardrail_desconto_vs_estoque(vendas: pd.DataFrame, estoque: pd.DataFrame) -> dict:
    """Teste 19: a empresa reage ao sinal de estoque crítico ao dar desconto?"""
    criticos = set(estoque.loc[estoque["ruptura"] | estoque["abaixo_ponto_pedido"], "sku_id"])
    v = vendas.copy()
    v["sku_critico"] = v["sku_id"].isin(criticos)
    desconto_critico = float(v.loc[v["sku_critico"], "desconto_pct"].mean())
    desconto_normal = float(v.loc[~v["sku_critico"], "desconto_pct"].mean())
    return {"desconto_pct_sku_critico": desconto_critico, "desconto_pct_sku_normal": desconto_normal}
