"""Dashboard de gestão — Vértice Retail.

Entregável do case: "Painel com indicadores-chave para a diretoria acompanhar
margem, canais, clientes, operação e atendimento." Diferente do Painel Único
(Streamlit, solucao_final/app.py) — que é uma ferramenta de ação (recuperação
de receita, guardrails, memo) — este é só leitura: um retrato executivo do
negócio, sem IA e sem botão que dispare nada.

Layout: tela fixa (sem scroll), navegação lateral, uma seção por vez — como um
BI de verdade, não uma página que rola. Reaproveita as mesmas fórmulas
validadas (solucao_final/src/metrics.py) e a mesma paleta CVD-safe de gráficos
(solucao_final/src/theme.py) do Painel Único — os números aqui nunca podem
divergir dos números de lá, porque vêm do mesmo código, não de uma
reimplementação.
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "solucao_final"))

from src import metrics, theme  # noqa: E402
from src.data import filtrar_vendas, load_all  # noqa: E402

data = load_all()
VENDAS, CLIENTES, ESTOQUE, ATENDIMENTO = data["vendas"], data["clientes"], data["estoque"], data["atendimento"]
DMIN, DMAX = VENDAS["data_pedido"].min().date(), VENDAS["data_pedido"].max().date()
CANAIS = sorted(VENDAS["canal"].unique())
CATEGORIAS = sorted(VENDAS["categoria"].unique())

SECOES = [
    ("geral", "Visão Geral"),
    ("margem", "Margem"),
    ("canais", "Canais"),
    ("clientes", "Clientes"),
    ("operacao", "Operação"),
    ("atendimento", "Atendimento"),
]


# ------------------------------------------------------------- componentes --
# Chrome tokens locais — distintos dos tokens de dado em theme.py de propósito:
# aqui é a paleta de TIPOGRAFIA/CHROME desta página (ver assets/style.css),
# as cores de DADO nos gráficos continuam vindo de theme.py (CVD-safe).
INK_2 = "#4A4D54"


def hero_stat(label: str, value: str, note: str | None = None, kind: str = "neutral") -> html.Div:
    """O número que manda na tela — um por seção, não quatro brigando pela
    mesma atenção. kind colore só quando o valor É o risco/ganho em si."""
    cls = "hero-value" + (f" {kind}" if kind != "neutral" else "")
    children = [html.Div(value, className=cls), html.Div(label, className="hero-label")]
    if note:
        children.append(html.Div(note, className="hero-note"))
    return html.Div(children, className="hero")


def stat(label: str, value: str, kind: str = "neutral") -> html.Div:
    cls = "stat-value" + (f" {kind}" if kind != "neutral" else "")
    return html.Div([html.Div(value, className=cls), html.Div(label, className="stat-label")], className="stat")


def hero_row(hero: html.Div, *stats) -> html.Div:
    return html.Div([hero, html.Div(list(stats), className="stat-row")], className="hero-row")


def chart_card(caption: str, fig: go.Figure) -> html.Div:
    return html.Div([
        html.Div(caption, className="chart-title"),
        html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}, style={"height": "100%", "width": "100%"}), className="chart-body"),
    ], className="chart-card")


def value_list_card(caption: str, rows: list[tuple[str, str]]) -> html.Div:
    """Alternativa ao gráfico de barra quando os valores são parecidos demais
    entre si (poucas categorias, diferença de fração de ponto) — nesses casos
    o comprimento da barra viraria ruído, não sinal, porque o eixo se
    auto-ajusta ao intervalo mínimo e exagera uma diferença trivial."""
    linhas = [
        html.Div([html.Span(label, className="vl-label"), html.Span(value, className="vl-value")], className="vl-row")
        for label, value in rows
    ]
    return html.Div([
        html.Div(caption, className="chart-title"),
        html.Div(linhas, className="value-list"),
    ], className="chart-card")


def chart_grid(*cards) -> html.Div:
    cards = list(cards)
    cls = "chart-grid single" if len(cards) == 1 else "chart-grid"
    if len(cards) > 2 and len(cards) % 2:
        cards[-1] = html.Div(cards[-1].children, className=cards[-1].className + " wide")
    return html.Div(cards, className=cls)


def _compacto(fig: go.Figure) -> go.Figure:
    """Reduz fonte/margens sem perder o resto do PLOTLY_LAYOUT — usa
    update_xaxes/update_yaxes (merge real do Plotly), nunca um override no
    style_fig (que faz merge raso e apagaria gridcolor/linecolor)."""
    fig.update_layout(font=dict(family=theme.FONT_STACK, color=INK_2, size=9.5), margin=dict(l=8, r=8, t=6, b=6))
    fig.update_xaxes(tickfont=dict(size=9))
    fig.update_yaxes(tickfont=dict(size=9))
    return fig


def _bar(x, y, color, horizontal=False, text=None, autorange_margin=True):
    kw = dict(orientation="h") if horizontal else {}
    label_font = dict(theme.DATA_LABEL_FONT, size=9)
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=color, text=text, textposition="outside", textfont=label_font, cliponaxis=False, **kw))
    theme.style_fig(fig, showlegend=False)
    _compacto(fig)
    if horizontal and autorange_margin:
        max_len = max((len(str(v)) for v in y), default=6)
        fig.update_layout(margin=dict(l=min(max(60, max_len * 5.5), 150), r=40, t=6, b=6))
    else:
        fig.update_layout(margin=dict(l=8, r=30, t=6, b=24))
    return fig


def _line(x, y, color, hovertemplate=None):
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color=color, width=2, shape="spline", smoothing=0.3),
        marker=dict(size=5, color=color, line=dict(width=1.2, color=theme.SURFACE)),
        fill="tozeroy", fillcolor=theme.hex_to_rgba(color, 0.10), hovertemplate=hovertemplate,
    ))
    theme.style_fig(fig, showlegend=False)
    _compacto(fig)
    fig.update_layout(margin=dict(l=8, r=8, t=6, b=20))
    return fig


def _fmt_pp(v: float, decimals: int = 1) -> str:
    return theme.fmt_pct(v, decimals).replace("%", " p.p.")


# ------------------------------------------------------------------ layout --
app = dash.Dash(__name__, title="Painel de Gestão · Vértice Retail")
server = app.server

app.index_string = """<!DOCTYPE html>
<html>
<head>
{%metas%}
<title>{%title%}</title>
{%favicon%}
{%css%}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""


app.layout = html.Div(className="shell", children=[
    html.Div(className="sidebar", children=[
        html.Div([
            html.Div("Painel de Gestão", className="brand-name"),
            html.Div("Vértice Retail", className="brand-sub"),
        ], className="brand"),
        dcc.Store(id="secao-ativa", data="margem"),
        html.Div(id="nav", className="nav"),
    ]),
    html.Div(className="main", children=[
        html.Div(className="filter-bar", children=[
            html.Div([
                html.Label("Período (vendas)", className="filter-label"),
                dcc.DatePickerRange(
                    id="filtro-periodo", min_date_allowed=DMIN, max_date_allowed=DMAX,
                    start_date=DMIN, end_date=DMAX, display_format="DD/MM/YY",
                ),
            ], className="filter"),
            html.Div([
                html.Label("Canal", className="filter-label"),
                dcc.Dropdown(
                    id="filtro-canal", options=[{"label": c, "value": c} for c in CANAIS],
                    multi=True, placeholder="Todos os canais", style={"width": "220px"},
                ),
            ], className="filter"),
            html.Div([
                html.Label("Categoria", className="filter-label"),
                dcc.Dropdown(
                    id="filtro-categoria", options=[{"label": c, "value": c} for c in CATEGORIAS],
                    multi=True, placeholder="Todas as categorias", style={"width": "220px"},
                ),
            ], className="filter"),
            html.Div("Canal não se aplica em Canais; categoria e período não se aplicam em Clientes/Atendimento.", className="filter-note"),
        ]),
        html.Div(className="topbar", children=[
            html.H1(id="page-title", className="page-title"),
            html.P(id="page-sub", className="page-sub"),
        ]),
        html.Div(id="conteudo", style={"flex": "1", "minHeight": "0", "display": "flex", "flexDirection": "column", "overflow": "hidden"}),
    ]),
])


# --------------------------------------------------------------- callbacks --
@app.callback(
    Output("secao-ativa", "data"),
    Input({"type": "navitem", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def trocar_secao(_):
    trig = dash.callback_context.triggered_id
    if not trig:
        raise dash.exceptions.PreventUpdate
    return trig["index"]


@app.callback(
    Output("nav", "children"),
    Output("page-title", "children"),
    Output("page-sub", "children"),
    Output("conteudo", "children"),
    Input("secao-ativa", "data"),
    Input("filtro-periodo", "start_date"),
    Input("filtro-periodo", "end_date"),
    Input("filtro-canal", "value"),
    Input("filtro-categoria", "value"),
)
def render(secao, data_ini, data_fim, canais, categorias):
    canais = canais or []
    categorias = categorias or []
    nav = [
        html.Div(label, id={"type": "navitem", "index": chave}, n_clicks=0,
                  className="navitem active" if chave == secao else "navitem")
        for chave, label in SECOES
    ]
    v_periodo = filtrar_vendas(VENDAS, data_ini, data_fim, [])       # só período (+ categoria) — usado por Canais
    v_filtrada = filtrar_vendas(VENDAS, data_ini, data_fim, canais)  # período + canal (+ categoria) — Margem e Operação
    if categorias:
        v_periodo = v_periodo[v_periodo["categoria"].isin(categorias)]
        v_filtrada = v_filtrada[v_filtrada["categoria"].isin(categorias)]

    construtores = {
        "geral": lambda: _secao_geral(v_periodo),
        "margem": lambda: _secao_margem(v_filtrada),
        "canais": lambda: _secao_canais(v_periodo),
        "clientes": lambda: _secao_clientes(),
        "operacao": lambda: _secao_operacao(v_filtrada),
        "atendimento": lambda: _secao_atendimento(),
    }
    titulo = dict(SECOES).get(secao, "Margem")
    if v_filtrada.empty and secao in ("margem", "operacao"):
        return nav, titulo, "Nenhum pedido no filtro selecionado.", html.Div("Ajuste o período ou o canal acima.", className="empty-state")
    if v_periodo.empty and secao in ("geral", "canais"):
        return nav, titulo, "Nenhum pedido no filtro selecionado.", html.Div("Ajuste o período ou a categoria acima.", className="empty-state")

    sub, corpo = construtores.get(secao, construtores["margem"])()
    return nav, titulo, sub, corpo


# --------------------------------------------------------------- seções -----
def _secao_geral(v):
    """Capa executiva — uma frase de síntese (não um número solto), os totais
    de cada domínio, e uma prévia pequena de um gráfico por aba. Ignora o
    filtro de canal pelo mesmo motivo que Canais ignora: a frase compara
    canais entre si."""
    margem = metrics.margem_realizada(v)
    gap = metrics.gap_marketplace(v)
    dev = metrics.devolucao_geral(v)
    skus = metrics.skus_criticos_curva_a(metrics.curva_abc(v, ESTOQUE), v)

    gap_txt = f" O Marketplace, sozinho, opera {_fmt_pp(gap['gap_margem_pp'])} abaixo dos demais canais." if "gap_margem_pp" in gap else ""
    headline = html.P(
        f"{theme.fmt_brl(margem['gap'])} de margem contábil não viraram caixa no período selecionado.{gap_txt}",
        className="headline",
    )

    resumo = html.Div([
        stat("Receita líquida", theme.fmt_brl(v["receita_liquida"].sum())),
        stat("Margem realizada", theme.fmt_pct(margem["pct_realizado"])),
        stat("Pedidos devolvidos", theme.fmt_pct(dev["pct_pedidos"])),
        stat("SKUs críticos na curva A", str(skus["n_criticos"])),
        stat("Receita em risco / ano", theme.fmt_brl(skus["receita_em_risco_anual"]), "critical"),
    ], className="stat-row overview")

    mensal = metrics.margem_mensal(v)
    fig_margem = _line(mensal["mes"], mensal["margem_pct_realizada"] * 100, theme.CAT_BLUE,
                        hovertemplate="%{x|%b/%y}<br>%{y:.1f}%<extra></extra>")
    tabela = gap["tabela"].sort_values("margem_pct") if "tabela" in gap else None
    fig_canais = _bar(tabela["margem_pct"] * 100, tabela["canal"],
                       [theme.CRITICAL if c == "Marketplace" else theme.CAT_BLUE for c in tabela["canal"]],
                       horizontal=True) if tabela is not None else go.Figure()
    seg = metrics.clientes_por_segmento(CLIENTES)
    cores_seg = [theme.CRITICAL if s in metrics.SEGMENTOS_RISCO else theme.CAT_BLUE for s in seg["segmento_rfm"]]
    fig_clientes = _bar(seg["segmento_rfm"], seg["ltv_total"], cores_seg)
    cat = metrics.atendimento_por_categoria(ATENDIMENTO).sort_values("tickets")
    fig_atend = _bar(cat["tickets"], cat["categoria_problema"], theme.CAT_ORANGE, horizontal=True)

    preview = chart_grid(
        chart_card("Margem realizada por mês", fig_margem),
        chart_card("Margem por canal", fig_canais),
        chart_card("LTV por segmento RFM", fig_clientes),
        chart_card("Chamados por categoria", fig_atend),
    )

    corpo = html.Div([headline, resumo, preview], style={"display": "flex", "flexDirection": "column", "flex": "1", "minHeight": "0"})
    return "", corpo


TETO_DESCONTO_PCT = 20  # política vigente — solucao_final/config/recuperacao.yaml (politica.teto_desconto_pct)


def _secao_margem(v):
    mensal = metrics.margem_mensal(v)
    margem = metrics.margem_realizada(v)
    desconto = metrics.desconto_geral(v)
    faixa = metrics.desconto_por_faixa(v)
    teto = metrics.simular_teto_desconto(v, TETO_DESCONTO_PCT)
    por_categoria = metrics.margem_por_categoria(v)
    cmv = metrics.cmv_estabilidade(v)

    hero = hero_row(
        hero_stat("Margem que não vira caixa", theme.fmt_brl(margem["gap"]),
                   f"{theme.fmt_pct(margem['pct_realizado'])} realizada vs. {theme.fmt_pct(margem['pct_contabil'])} contábil — devolução, cancelamento e pagamento pendente", "critical"),
        stat("Receita líquida", theme.fmt_brl(v["receita_liquida"].sum())),
        stat("Desconto médio", theme.fmt_pct(desconto["pct_receita_bruta"]),
             "warning" if desconto["pct_receita_bruta"] > 0.05 else "neutral"),
        stat(f"Acima do teto de {TETO_DESCONTO_PCT}%", theme.fmt_pct(teto["pct_pedidos_acima"]), "warning"),
    )

    fig_trend = _line(mensal["mes"], mensal["margem_pct_realizada"] * 100, theme.CAT_BLUE,
                       hovertemplate="%{x|%b/%y}<br>%{y:.1f}%<extra></extra>")
    fig_faixa = _bar(faixa["faixa_desconto"].astype(str), faixa["margem_pct_media"] * 100, theme.ORDINAL_BLUE_6[:len(faixa)],
                      text=[f"{x:.0f}%" for x in faixa["margem_pct_media"] * 100])
    cmv_cat = cmv["por_categoria"].sort_values(ascending=False)
    por_categoria = por_categoria.sort_values("margem_pct", ascending=False)

    corpo = html.Div([hero, chart_grid(
        chart_card("Margem realizada por mês", fig_trend),
        chart_card("Margem média por faixa de desconto", fig_faixa),
        value_list_card("Margem por categoria (as 4 são iguais — mix não é o problema)",
                         [(cat, theme.fmt_pct(x)) for cat, x in zip(por_categoria["categoria"], por_categoria["margem_pct"])]),
        value_list_card(f"CMV por categoria (estável — {theme.fmt_pct(cmv['amplitude_pp'])} de amplitude)",
                         [(cat, f"{x*100:.1f}%".replace(".", ",")) for cat, x in cmv_cat.items()]),
    )], style={"display": "flex", "flexDirection": "column", "flex": "1", "minHeight": "0"})
    return "Quanto da receita realmente vira margem, e como o desconto se relaciona com essa margem.", corpo


def _secao_canais(v):
    gap = metrics.gap_marketplace(v)
    tabela = gap["tabela"].sort_values("margem_pct")
    fig_margem = _bar(tabela["margem_pct"] * 100, tabela["canal"],
                       [theme.CRITICAL if c == "Marketplace" else theme.CAT_BLUE for c in tabela["canal"]],
                       horizontal=True, text=[theme.fmt_pct(x) for x in tabela["margem_pct"]])
    tabela_frete = gap["tabela"].sort_values("frete_pct", ascending=False)
    fig_frete = _bar(tabela_frete["frete_pct"] * 100, tabela_frete["canal"],
                      [theme.CRITICAL if c == "Marketplace" else theme.CAT_ORANGE for c in tabela_frete["canal"]],
                      horizontal=True, text=[theme.fmt_pct(x) for x in tabela_frete["frete_pct"]])
    tabela_receita = gap["tabela"].sort_values("receita_liquida")
    fig_receita = _bar(tabela_receita["receita_liquida"], tabela_receita["canal"], theme.CAT_BLUE,
                        horizontal=True, text=[theme.fmt_brl(x) for x in tabela_receita["receita_liquida"]])
    dev_canal = metrics.devolucao_por_canal(v).sort_values("taxa_devolucao", ascending=False)

    hero = None
    if "gap_frete_r" in gap:
        hero = hero_row(
            hero_stat("Gap de margem — Marketplace", theme.fmt_brl(gap["gap_margem_r"]) + "/ano",
                       f"{_fmt_pp(gap['gap_margem_pp'])} abaixo dos demais canais", "critical"),
            stat("Gap de frete — Marketplace", _fmt_pp(gap["gap_frete_pp"]), "warning"),
            stat("Receita do canal", theme.fmt_brl(gap["receita_marketplace"])),
        )

    caveat = html.Div("Calculado a partir de vendas.csv.", className="caveat")

    filhos = [caveat, hero] if hero else [caveat]
    filhos.append(chart_grid(
        chart_card("Margem por canal", fig_margem),
        chart_card("Frete como % da receita, por canal", fig_frete),
        chart_card("Receita líquida por canal", fig_receita),
        value_list_card("Taxa de devolução por canal (parecida entre todos — menos de 1 p.p. de amplitude)",
                         [(c, theme.fmt_pct(x)) for c, x in zip(dev_canal["canal"], dev_canal["taxa_devolucao"])]),
    ))
    corpo = html.Div(filhos, style={"display": "flex", "flexDirection": "column", "flex": "1", "minHeight": "0"})
    return "Sempre com todos os canais — filtrar por canal aqui esvaziaria a própria comparação.", corpo


def _secao_clientes():
    kpis = metrics.clientes_kpis(CLIENTES)
    seg = metrics.clientes_por_segmento(CLIENTES)
    fid = metrics.clientes_por_fidelidade(CLIENTES)

    hero = hero_row(
        hero_stat("LTV em segmentos de risco", theme.fmt_brl(kpis["ltv_em_risco"]),
                   f"{theme.fmt_pct(kpis['pct_em_risco'])} da base em Em Risco, Hibernando ou Churn", "critical"),
        stat("Clientes cadastrados", theme.fmt_num(kpis["n_clientes"])),
        stat("LTV médio", theme.fmt_brl(kpis["ltv_medio"]) + "/cliente"),
    )

    cores = [theme.CRITICAL if s in metrics.SEGMENTOS_RISCO else theme.CAT_BLUE for s in seg["segmento_rfm"]]
    fig_seg = _bar(seg["segmento_rfm"], seg["ltv_total"], cores, text=[theme.fmt_brl(x) for x in seg["ltv_total"]])
    fig_seg_n = _bar(seg["segmento_rfm"], seg["n_clientes"], cores, text=[theme.fmt_num(x) for x in seg["n_clientes"]])
    fig_fid = _bar(fid["nivel_fidelidade"], fid["ltv_medio"], theme.ORDINAL_BLUE_6[:len(fid)],
                    text=[theme.fmt_brl(x) for x in fid["ltv_medio"]])
    fig_fid_n = _bar(fid["nivel_fidelidade"], fid["n_clientes"], theme.ORDINAL_BLUE_6[:len(fid)],
                      text=[theme.fmt_num(x) for x in fid["n_clientes"]])

    corpo = html.Div([
        html.Div("Calculado a partir de clientes.csv isoladamente/re.", className="caveat"),
        hero,
        chart_grid(
            chart_card("LTV acumulado por segmento RFM", fig_seg),
            chart_card("Clientes por segmento RFM", fig_seg_n),
            chart_card("LTV médio por nível de fidelidade", fig_fid),
            chart_card("Clientes por nível de fidelidade", fig_fid_n),
        ),
    ], style={"display": "flex", "flexDirection": "column", "flex": "1", "minHeight": "0"})
    return "Segmentação RFM e valor acumulado da base de clientes.", corpo


def _secao_operacao(v):
    curva = metrics.curva_abc(v, ESTOQUE)
    skus = metrics.skus_criticos_curva_a(curva, v)
    dev = metrics.devolucao_geral(v)
    dev_motivo = metrics.devolucao_por_motivo(v)
    dev_fornecedor = metrics.devolucao_por_fornecedor(v, ESTOQUE)
    parado = metrics.estoque_parado(ESTOQUE)

    hero = hero_row(
        hero_stat("Receita em risco por ano", theme.fmt_brl(skus["receita_em_risco_anual"]),
                   f"{skus['n_criticos']} de {skus['total_curva_a']} SKUs da curva A em ruptura ou estoque crítico", "critical"),
        stat("Pedidos devolvidos", theme.fmt_pct(dev["pct_pedidos"])),
        stat("Margem perdida endereçável", theme.fmt_brl(dev["margem_perdida_enderecavel"]), "warning"),
        stat("Estoque parado (2+ anos)", theme.fmt_pct(parado["pct_parado_2anos"]), "warning"),
    )

    cores = [theme.CRITICAL if e else theme.REF_GRAY for e in dev_motivo["enderecavel"]]
    fig_motivo = _bar(dev_motivo["margem_perdida"], dev_motivo["motivo_devolucao"], cores,
                       horizontal=True, text=[theme.fmt_brl(x) for x in dev_motivo["margem_perdida"]])
    fig_fornecedor = _bar(dev_fornecedor["margem_perdida"], dev_fornecedor["fornecedor_id"], theme.CAT_ORANGE,
                           horizontal=True, text=[theme.fmt_brl(x) for x in dev_fornecedor["margem_perdida"]])
    skus_cat = metrics.skus_criticos_por_categoria(curva)
    fig_skus_cat = _bar(skus_cat["n_criticos"], skus_cat["categoria"], theme.CRITICAL,
                         horizontal=True, text=[theme.fmt_num(x) for x in skus_cat["n_criticos"]])
    parado_cat = metrics.estoque_parado_por_categoria(ESTOQUE).sort_values("pct_parado_2anos", ascending=False)

    corpo = html.Div([hero, chart_grid(
        chart_card("Margem perdida por motivo (vermelho = endereçável)", fig_motivo),
        chart_card("Margem perdida por fornecedor (só causa endereçável)", fig_fornecedor),
        chart_card("SKUs críticos da curva A, por categoria", fig_skus_cat),
        value_list_card("Estoque parado 2+ anos, por categoria (parecido em todas)",
                         [(c, theme.fmt_pct(x)) for c, x in zip(parado_cat["categoria"], parado_cat["pct_parado_2anos"])]),
    )], style={"display": "flex", "flexDirection": "column", "flex": "1", "minHeight": "0"})
    return ("Estoque (ruptura nos produtos que mais vendem) e devolução (o que a empresa pode corrigir). "
            "Estoque é uma fotografia do momento, não uma série no tempo — leia como direcional."), corpo


def _secao_atendimento():
    cat = metrics.atendimento_por_categoria(ATENDIMENTO)
    chatbot = metrics.chatbot_economia(ATENDIMENTO)
    falha = metrics.volume_falha_operacional(ATENDIMENTO)

    hero = hero_row(
        hero_stat("Economia potencial com o ChatBot", theme.fmt_brl(chatbot["economia_anual"]) + "/ano",
                   f"migrando atendimento simples, com CSAT de {theme.fmt_num(chatbot['csat_chatbot'], 2)} contra {theme.fmt_num(chatbot['csat_humano'], 2)} do atendimento humano", "good"),
        stat("Volume de tickets", theme.fmt_num(len(ATENDIMENTO))),
        stat("Falha operacional", theme.fmt_pct(falha["pct_tickets_falha"]), "warning"),
    )

    cat_sorted = cat.sort_values("tickets")
    fig_cat = _bar(cat_sorted["tickets"], cat_sorted["categoria_problema"], theme.CAT_ORANGE, horizontal=True)
    fig_custo = _bar(["ChatBot", "Canais humanos"], [chatbot["custo_medio_chatbot"], chatbot["custo_medio_humano"]],
                      [theme.CAT_BLUE, theme.REF_GRAY],
                      text=[theme.fmt_brl(chatbot["custo_medio_chatbot"], 2), theme.fmt_brl(chatbot["custo_medio_humano"], 2)])
    por_canal = metrics.atendimento_por_canal(ATENDIMENTO).sort_values("tickets")
    fig_canal = _bar(por_canal["tickets"], por_canal["canal_entrada"],
                      [theme.CAT_BLUE if c == "ChatBot" else theme.REF_GRAY for c in por_canal["canal_entrada"]],
                      horizontal=True, text=[theme.fmt_num(x) for x in por_canal["tickets"]])
    cat_csat = cat.sort_values("csat_medio")
    fig_csat = _bar(cat_csat["csat_medio"], cat_csat["categoria_problema"], theme.CAT_AQUA,
                     horizontal=True, text=[f"{x:.2f}".replace(".", ",") for x in cat_csat["csat_medio"]])

    corpo = html.Div([hero, chart_grid(
        chart_card("Volume de chamados por categoria", fig_cat),
        chart_card("Custo médio por ticket (R$)", fig_custo),
        chart_card("Volume de chamados por canal de entrada", fig_canal),
        chart_card("CSAT médio por categoria de problema", fig_csat),
    )], style={"display": "flex", "flexDirection": "column", "flex": "1", "minHeight": "0"})
    return "Onde o custo de atendimento se concentra e onde a automação já provou funcionar.", corpo


if __name__ == "__main__":
    app.run(debug=True, port=8060)
