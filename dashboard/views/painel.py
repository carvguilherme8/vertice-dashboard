from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import metrics, theme
from src.data import filtrar_vendas, load_all
from src.recuperacao import planner, registro
from src.recuperacao.config import carregar_config
from src.recuperacao.llm import OllamaIndisponivel


# --------------------------------------------------------------- chart utils
def _bar(x, y, color, title=None, horizontal=False, text=None, height=260, xaxis_title=None, yaxis_title=None):
    """x, y sempre na convenção (categoria, valor) para barras verticais e
    (valor, categoria) para horizontais — quem chama já passa nessa ordem;
    aqui só repassamos direto para o go.Bar, sem inverter."""
    kw = dict(orientation="h") if horizontal else {}
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=color, text=text, textposition="outside", textfont=theme.DATA_LABEL_FONT, cliponaxis=False, **kw))
    margin = dict(l=10, r=70, t=40 if title else 14, b=36)
    if horizontal:
        labels = y
        max_len = max((len(str(v)) for v in labels), default=8)
        margin["l"] = min(max(90, max_len * 6 + 20), 230)
        margin["b"] = 14
        fig.update_yaxes(automargin=True)
    theme.style_fig(fig, title=title, height=height, showlegend=False, xaxis_title=xaxis_title, yaxis_title=yaxis_title, margin=margin)
    return fig


def _line(x, y, color, title=None, height=240, yaxis_title=None, hovertemplate=None):
    fig = go.Figure(
        go.Scatter(
            x=x, y=y, mode="lines+markers",
            line=dict(color=color, width=2.5, shape="spline", smoothing=0.3),
            marker=dict(size=7, color=color, line=dict(width=1.5, color=theme.SURFACE)),
            fill="tozeroy", fillcolor=theme.hex_to_rgba(color, 0.10), hovertemplate=hovertemplate,
        )
    )
    theme.style_fig(fig, title=title, height=height, showlegend=False, yaxis_title=yaxis_title, margin=dict(l=10, r=10, t=40 if title else 14, b=30))
    return fig


def render():
    data = load_all()
    vendas_full, estoque, atendimento = data["vendas"], data["estoque"], data["atendimento"]
    dmin, dmax = vendas_full["data_pedido"].min().date(), vendas_full["data_pedido"].max().date()

    h1, h2, h3 = st.columns([2.6, 1.3, 1.7], vertical_alignment="center")
    with h1:
        st.markdown(
            '<div class="app-title"><h1>Painel Único de Decisão Comercial</h1>'
            '<div class="sub">Recuperação de receita pós-venda · Prevenção de devolução na origem · '
            'Priorizador de margem · Memo executivo · Vértice Retail</div></div>',
            unsafe_allow_html=True,
        )
    with h2:
        periodo = st.date_input("Período", value=(dmin, dmax), min_value=dmin, max_value=dmax, label_visibility="collapsed")
    with h3:
        canais = st.multiselect("Canal", sorted(vendas_full["canal"].unique()), default=[], placeholder="Todos os canais", label_visibility="collapsed")
    st.markdown('<div class="header-divider"></div>', unsafe_allow_html=True)

    data_ini, data_fim = periodo if isinstance(periodo, tuple) and len(periodo) == 2 else (dmin, dmax)
    vendas = filtrar_vendas(vendas_full, data_ini, data_fim, canais)
    if vendas.empty:
        st.warning("Nenhum pedido no filtro selecionado — ajuste o período ou o canal acima.")
        return

    mensal = metrics.margem_mensal(vendas)
    _kpis(vendas, mensal)
    _alertas(vendas, estoque)

    tab_e, tab_dev, tab_c, tab_d = st.tabs([
        "Recuperação de receita pós-venda", "Prevenção de devolução na origem",
        "Priorizador de margem", "Memo executivo",
    ])
    with tab_e:
        _modulo_recuperacao(vendas_full)
    with tab_dev:
        _modulo_devolucao(vendas, estoque)
    with tab_c:
        _modulo_c(vendas, estoque)
    with tab_d:
        _modulo_d(vendas, estoque, atendimento, mensal, data_ini, data_fim)


def _kpis(vendas: pd.DataFrame, mensal: pd.DataFrame):
    margem = metrics.margem_realizada(vendas)
    desconto = metrics.desconto_geral(vendas)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(theme.stat_tile("Margem realizada", theme.fmt_pct(margem["pct_realizado"]), f"vs. {theme.fmt_pct(margem['pct_contabil'])} contábil", "neutral", mensal["margem_pct_realizada"] * 100, theme.CAT_BLUE), unsafe_allow_html=True)
    with c2:
        st.markdown(theme.stat_tile("Margem não realizada", theme.fmt_brl(margem["gap"]), "devolução + cancel. + pendente", "critical", (mensal["margem_contabil"] - mensal["margem_realizada"]), theme.CRITICAL), unsafe_allow_html=True)
    with c3:
        st.markdown(theme.stat_tile("Desconto concedido", theme.fmt_brl(desconto["total"]), f"{theme.fmt_pct(desconto['pct_pedidos_com_desconto'])} dos pedidos", "warning", mensal["desconto_reais"], theme.WARNING), unsafe_allow_html=True)
    with c4:
        st.markdown(theme.stat_tile("Receita líquida", theme.fmt_brl(vendas["receita_liquida"].sum()), f"{theme.fmt_num(len(vendas))} pedidos", "good", mensal["receita_liquida"], theme.GOOD), unsafe_allow_html=True)


def _alertas(vendas: pd.DataFrame, estoque: pd.DataFrame):
    curva = metrics.curva_abc(vendas, estoque)
    skus = metrics.skus_criticos_curva_a(curva, vendas)
    n_ruptura = int(estoque["ruptura"].sum())
    sim = metrics.simular_teto_desconto(vendas, 25)

    st.markdown(
        '<div class="alert-row">'
        + theme.alert_card("critical", f"<b>{n_ruptura} SKUs em ruptura</b> na base · <b>{skus['n_criticos']}</b> críticos na curva A de alto giro")
        + theme.alert_card("warning", f"<b>{theme.fmt_brl(sim['desconto_concedido_acima'])}</b> concedidos acima de 25% de desconto no período")
        + theme.alert_card("info", f"<b>{theme.fmt_brl(skus['receita_em_risco_anual'])}/ano</b> em risco se a ruptura persistir")
        + "</div>",
        unsafe_allow_html=True,
    )


def _modulo_c(vendas: pd.DataFrame, estoque: pd.DataFrame):
    st.markdown('<div class="section-title">Guardrail 1 · Teto de desconto por faixa</div>', unsafe_allow_html=True)
    teto = st.slider(
        "Teto de desconto (%)", min_value=0, max_value=40, value=25, step=1, key="teto_desconto",
        help="Unidades por pedido não sobem com o desconto — acima do teto, o desconto é margem cedida sem contrapartida de volume.",
    )
    sim = metrics.simular_teto_desconto(vendas, teto)
    delta_margem = (sim["margem_pct_dentro"] - sim["margem_pct_acima"]) if sim["margem_pct_acima"] is not None and sim["margem_pct_dentro"] is not None else None

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(theme.stat_tile("Pedidos acima do teto", theme.fmt_num(sim["n_pedidos_acima"]), f"{theme.fmt_pct(sim['pct_pedidos_acima'])} do total", "warning"), unsafe_allow_html=True)
    with c2:
        st.markdown(theme.stat_tile("Recuperável se a regra for aplicada", theme.fmt_brl(sim["desconto_concedido_acima"]), None, "good"), unsafe_allow_html=True)
    with c3:
        delta_txt = f"+{theme.fmt_pct(delta_margem)} vs. acima do teto" if delta_margem is not None else None
        st.markdown(theme.stat_tile("Margem % dentro do teto", theme.fmt_pct(sim["margem_pct_dentro"]), delta_txt, "good"), unsafe_allow_html=True)

    faixa = metrics.desconto_por_faixa(vendas)
    cc1, cc2 = st.columns(2)
    with cc1:
        fig = _bar(faixa["faixa_desconto"].astype(str), faixa["margem_pct_media"] * 100, theme.ORDINAL_BLUE_6[: len(faixa)], "Margem % média por faixa de desconto", text=[f"{v:.0f}%" for v in faixa["margem_pct_media"] * 100])
        st.plotly_chart(fig, use_container_width=True, theme=None)
    with cc2:
        fig = _bar(faixa["faixa_desconto"].astype(str), faixa["pedidos"], theme.CAT_BLUE, "Volume de pedidos por faixa", text=[f"{v:,}".replace(",", ".") for v in faixa["pedidos"]])
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with st.expander(f"{min(20, sim['n_pedidos_acima'])} maiores pedidos que a regra bloquearia"):
        acima = vendas[vendas["desconto_pct"] > teto / 100].sort_values("desconto_reais", ascending=False).head(20)
        st.dataframe(
            acima[["order_id", "canal", "categoria", "produto", "desconto_pct", "desconto_reais", "margem_pct"]],
            hide_index=True, use_container_width=True,
            column_config={
                "desconto_pct": st.column_config.NumberColumn("Desconto %", format="%.1f%%"),
                "desconto_reais": st.column_config.NumberColumn("Desconto R$", format="R$ %.2f"),
                "margem_pct": st.column_config.NumberColumn("Margem %", format="%.1f%%"),
            },
        )

    st.markdown('<div class="section-title">Guardrail 2 · Reposição dirigida aos SKUs críticos</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Curva A = 80% da receita do período · crítico = ruptura ou abaixo do ponto de pedido</div>', unsafe_allow_html=True)

    curva = metrics.curva_abc(vendas, estoque)
    skus = metrics.skus_criticos_curva_a(curva, vendas)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(theme.stat_tile("SKUs críticos na curva A", f"{skus['n_criticos']} / {skus['total_curva_a']}", f"{theme.fmt_pct(skus['pct_da_curva_a'])} da curva A", "critical"), unsafe_allow_html=True)
    with c2:
        st.markdown(theme.stat_tile("Receita em risco / ano", theme.fmt_brl(skus["receita_em_risco_anual"]), "extrapolação", "critical"), unsafe_allow_html=True)
    with c3:
        st.markdown(theme.stat_tile("Receita em risco / dia", theme.fmt_brl(skus["receita_dia_risco"]), None, "neutral"), unsafe_allow_html=True)

    tabela = skus["tabela"].copy()
    tabela["status"] = tabela["ruptura"].map({True: "Ruptura"}).fillna("Abaixo do ponto de pedido")

    top10 = tabela.head(10).sort_values("receita_liquida_periodo")
    fig = _bar(top10["receita_liquida_periodo"], top10["sku_id"] + " · " + top10["nome_produto"].str.slice(0, 18), theme.CRITICAL, "Top 10 SKUs críticos por receita em risco", horizontal=True, height=320)
    st.plotly_chart(fig, use_container_width=True, theme=None)

    filtro_status = st.radio("Filtrar tabela", ["Todos", "Ruptura", "Abaixo do ponto de pedido"], horizontal=True, key="filtro_sku", label_visibility="collapsed")
    if filtro_status != "Todos":
        tabela = tabela[tabela["status"] == filtro_status]
    st.dataframe(
        tabela[["sku_id", "nome_produto", "categoria", "fornecedor_id", "estoque_disponivel", "ponto_pedido", "lead_time_reposicao", "receita_liquida_periodo", "status"]],
        hide_index=True, use_container_width=True, height=280,
        column_config={
            "sku_id": "SKU", "nome_produto": "Produto", "fornecedor_id": "Fornecedor",
            "estoque_disponivel": "Estoque disp.", "ponto_pedido": "Ponto de pedido", "lead_time_reposicao": "Lead time (d)",
            "receita_liquida_periodo": st.column_config.NumberColumn("Receita no período", format="R$ %.0f"),
        },
    )

    st.markdown('<div class="section-title">Achado de processo · desconto reage ao sinal de estoque?</div>', unsafe_allow_html=True)
    guard = metrics.guardrail_desconto_vs_estoque(vendas, estoque)
    cc1, cc2 = st.columns([1, 2])
    with cc1:
        diff = abs(guard["desconto_pct_sku_critico"] - guard["desconto_pct_sku_normal"])
        if diff < 0.01:
            st.markdown(theme.alert_card("warning", "Desconto <b>não muda</b> diante de estoque crítico — o sinal existe e é ignorado."), unsafe_allow_html=True)
        else:
            st.markdown(theme.alert_card("info", "Há diferença perceptível entre o desconto de SKU crítico e normal."), unsafe_allow_html=True)
    with cc2:
        fig = _bar(
            ["SKU crítico", "SKU normal"],
            [guard["desconto_pct_sku_critico"] * 100, guard["desconto_pct_sku_normal"] * 100],
            [theme.CRITICAL, theme.REF_GRAY],
            "Desconto médio concedido (%)", height=220,
            text=[f"{guard['desconto_pct_sku_critico']*100:.2f}%", f"{guard['desconto_pct_sku_normal']*100:.2f}%"],
        )
        st.plotly_chart(fig, use_container_width=True, theme=None)


def _modulo_d(vendas: pd.DataFrame, estoque: pd.DataFrame, atendimento: pd.DataFrame, mensal: pd.DataFrame, data_ini, data_fim):
    margem = metrics.margem_realizada(vendas)
    desconto = metrics.desconto_geral(vendas)
    curva = metrics.curva_abc(vendas, estoque)
    skus = metrics.skus_criticos_curva_a(curva, vendas)
    gap_mkt = metrics.gap_marketplace(vendas)
    chatbot = metrics.chatbot_economia(atendimento)
    cmv = metrics.cmv_estabilidade(vendas)
    atend_cat = metrics.atendimento_por_categoria(atendimento)

    col_a, col_b = st.columns([1, 1.3])
    with col_a:
        fig = _bar(["Contábil", "Realizada"], [margem["contabil"], margem["realizado"]], [theme.REF_GRAY, theme.CAT_BLUE], "Margem contábil vs. realizada", text=[theme.fmt_brl(margem["contabil"]), theme.fmt_brl(margem["realizado"])], height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)
    with col_b:
        fig = _line(mensal["mes"], mensal["margem_pct_realizada"] * 100, theme.CAT_BLUE, "Margem % realizada — evolução mensal", height=300, hovertemplate="%{x|%b/%y}<br>%{y:.1f}%<extra></extra>")
        st.plotly_chart(fig, use_container_width=True, theme=None)

    col_c, col_d = st.columns(2)
    with col_c:
        if "gap_frete_r" in gap_mkt:
            fig = _bar(["Marketplace", "Demais canais"], [gap_mkt["frete_pct_marketplace"] * 100, gap_mkt["frete_pct_outros"] * 100], [theme.CRITICAL, theme.REF_GRAY], "Frete como % da receita do canal", height=260, text=[theme.fmt_pct(gap_mkt["frete_pct_marketplace"]), theme.fmt_pct(gap_mkt["frete_pct_outros"])])
            st.plotly_chart(fig, use_container_width=True, theme=None)
            st.markdown(theme.stat_tile("Vão de frete anualizado (Marketplace)", theme.fmt_brl(gap_mkt["gap_frete_r"]), None, "critical"), unsafe_allow_html=True)
    with col_d:
        fig = _bar(["ChatBot", "Canais humanos"], [chatbot["custo_medio_chatbot"], chatbot["custo_medio_humano"]], [theme.CAT_BLUE, theme.REF_GRAY], "Custo médio por ticket (R$)", height=260, text=[theme.fmt_brl(chatbot["custo_medio_chatbot"], 2), theme.fmt_brl(chatbot["custo_medio_humano"], 2)])
        st.plotly_chart(fig, use_container_width=True, theme=None)
        st.markdown(theme.stat_tile("Economia anualizada (ChatBot)", theme.fmt_brl(chatbot["economia_anual"]), f"CSAT {chatbot['csat_chatbot']:.2f} vs. {chatbot['csat_humano']:.2f}", "good"), unsafe_allow_html=True)

    col_e, col_f = st.columns(2)
    with col_e:
        ac_sorted = atend_cat.sort_values("tickets")
        fig = _bar(ac_sorted["tickets"], ac_sorted["categoria_problema"], theme.CAT_ORANGE, "Volume de chamados por categoria", horizontal=True, height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)
    with col_f:
        cmv_cat = cmv["por_categoria"].sort_values()
        fig = _bar(cmv_cat.values * 100, cmv_cat.index, theme.CAT_VIOLET, f"CMV % por categoria (estável — amplitude {theme.fmt_pct(cmv['amplitude_pp'])})", horizontal=True, height=300, text=[f"{v:.1f}%" for v in cmv_cat.values * 100])
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with st.expander("Memo executivo em texto — gerado automaticamente"):
        memo = _montar_memo(margem, desconto, skus, gap_mkt, chatbot, cmv, data_ini, data_fim)
        st.text_area("memo", memo, height=320, label_visibility="collapsed")
        st.download_button("Baixar memo (.md)", memo, file_name=f"memo_executivo_{data_fim}.md", mime="text/markdown")


def _montar_memo(margem, desconto, skus, gap_mkt, chatbot, cmv, data_ini, data_fim) -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    linhas = [
        f"# Memo executivo — Decisão comercial ({data_ini} a {data_fim})",
        f"_Gerado em {hoje} pelo Painel Único de Decisão Comercial · Priorizador de margem + Memo executivo_",
        "",
        "## Fato",
        f"- Margem contábil: {theme.fmt_brl(margem['contabil'])} ({theme.fmt_pct(margem['pct_contabil'])} da receita líquida)",
        f"- Margem realizada: {theme.fmt_brl(margem['realizado'])} ({theme.fmt_pct(margem['pct_realizado'])} da receita líquida)",
        f"- Desconto concedido no período: {theme.fmt_brl(desconto['total'])} ({theme.fmt_pct(desconto['pct_receita_bruta'])} da receita bruta)",
        f"- SKUs críticos na curva A: {skus['n_criticos']} de {skus['total_curva_a']} ({theme.fmt_pct(skus['pct_da_curva_a'])})",
        f"- CMV estável em {theme.fmt_pct(cmv['geral'])} (amplitude de {theme.fmt_pct(cmv['amplitude_pp'])} entre categorias — não é driver de margem)",
        "",
        "## Causa",
        f"- {theme.fmt_brl(margem['gap'])} de margem contábil não vira caixa por devolução, cancelamento ou pagamento pendente.",
        f"- {skus['n_criticos']} SKUs de alto giro estão em ruptura ou abaixo do ponto de pedido, colocando {theme.fmt_brl(skus['receita_em_risco_anual'])}/ano em risco se persistir.",
    ]
    if "gap_frete_r" in gap_mkt:
        linhas.append(f"- O Marketplace opera com {theme.fmt_pct(gap_mkt['gap_frete_pp'])} a mais de frete sobre a receita que os demais canais, um vão de {theme.fmt_brl(gap_mkt['gap_frete_r'])}/ano.")
    linhas += [
        "",
        "## Implicação",
        "- O desconto concedido não compra volume adicional — é margem cedida sem contrapartida.",
        f"- Migrar o atendimento simples para o ChatBot economiza {theme.fmt_brl(chatbot['economia_anual'])}/ano sem perda de qualidade percebida (CSAT {chatbot['csat_chatbot']:.2f} vs. {chatbot['csat_humano']:.2f}).",
        "",
        "## Recomendação",
        "1. Aplicar o teto de desconto por faixa (ver simulação em Priorizador de margem).",
        "2. Priorizar reposição dos SKUs críticos listados em Priorizador de margem.",
        "3. Redefinir a métrica de margem reportada à diretoria para a margem realizada.",
        "4. Abrir negociação de frete com o Marketplace.",
        "5. Migrar o volume simples de 'onde está meu pedido' para o ChatBot.",
    ]
    return "\n".join(linhas)


def _modulo_devolucao(vendas: pd.DataFrame, estoque: pd.DataFrame):
    geral = metrics.devolucao_geral(vendas)

    st.markdown('<div class="section-title">Devolução — causa operacional vs. decisão do cliente</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Endereçável = defeito, tamanho errado, atraso na entrega — a empresa controla a causa. '
        'Arrependimento e "não gostei" não entram: é decisão do cliente, não se elimina.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(theme.stat_tile("Pedidos devolvidos", theme.fmt_num(geral["n_devolvidos"]), f"{theme.fmt_pct(geral['pct_pedidos'])} do total", "warning"), unsafe_allow_html=True)
    with c2:
        st.markdown(theme.stat_tile("Margem perdida total", theme.fmt_brl(geral["margem_perdida_total"]), None, "critical"), unsafe_allow_html=True)
    with c3:
        st.markdown(theme.stat_tile("Endereçável (causa operacional)", theme.fmt_brl(geral["margem_perdida_enderecavel"]), "ação da empresa resolve", "critical"), unsafe_allow_html=True)
    with c4:
        st.markdown(theme.stat_tile("Não endereçável", theme.fmt_brl(geral["margem_perdida_nao_enderecavel"]), "decisão do cliente", "neutral"), unsafe_allow_html=True)

    motivo = metrics.devolucao_por_motivo(vendas)
    fornecedor = metrics.devolucao_por_fornecedor(vendas, estoque)

    cc1, cc2 = st.columns(2)
    with cc1:
        motivo_sorted = motivo.sort_values("margem_perdida")
        cores = [theme.CRITICAL if e else theme.REF_GRAY for e in motivo_sorted["enderecavel"]]
        fig = go.Figure(go.Bar(
            x=motivo_sorted["margem_perdida"], y=motivo_sorted["motivo_devolucao"], orientation="h",
            marker_color=cores, text=[theme.fmt_brl(v) for v in motivo_sorted["margem_perdida"]],
            textposition="outside", textfont=theme.DATA_LABEL_FONT, cliponaxis=False,
        ))
        fig.update_yaxes(automargin=True)
        theme.style_fig(fig, title="Margem perdida por motivo (vermelho = endereçável)", height=280, showlegend=False, margin=dict(l=140, r=70, t=40, b=14))
        st.plotly_chart(fig, use_container_width=True, theme=None)
    with cc2:
        fornecedor_sorted = fornecedor.sort_values("margem_perdida")
        fig = _bar(fornecedor_sorted["margem_perdida"], fornecedor_sorted["fornecedor_id"], theme.CAT_ORANGE, "Margem perdida por fornecedor (só causa operacional)", horizontal=True, height=280, text=[theme.fmt_brl(v) for v in fornecedor_sorted["margem_perdida"]])
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with st.expander("SKUs mais afetados por devolução de causa operacional"):
        sku = metrics.devolucao_por_sku(vendas, estoque)
        st.dataframe(
            sku, hide_index=True, use_container_width=True,
            column_config={
                "sku_id": "SKU", "nome_produto": "Produto", "fornecedor_id": "Fornecedor",
                "pedidos": "Pedidos devolvidos", "motivo_mais_comum": "Motivo mais comum",
                "margem_perdida": st.column_config.NumberColumn("Margem perdida", format="R$ %.0f"),
            },
        )


def _modulo_recuperacao(vendas_full: pd.DataFrame):
    st.markdown('<div class="section-title">Fila priorizada — pedidos com pagamento pendente ou cancelado</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Arquitetura Planejamento + Reflexão sobre scoring determinístico '
        '(v4/09 e v4/10) · LLM local via Ollama/Gemma, sem tool use</div>',
        unsafe_allow_html=True,
    )

    cfg = carregar_config()
    dmin, dmax = vendas_full["data_pedido"].min().date(), vendas_full["data_pedido"].max().date()

    c1, c2 = st.columns([1, 3])
    with c1:
        data_ref = st.date_input(
            "Data de referência da rodada (simula 'hoje')", value=dmax, min_value=dmin, max_value=dmax,
            key="rec_data_ref",
            help="O data room é um snapshot estático — mover esta data simula rodadas diferentes sobre o mesmo dado, sem precisar de dado novo chegar.",
        )
    with c2:
        st.markdown(
            f'<div style="padding-top:28px;color:{theme.MUTED};font-size:12.5px;">'
            f'Modelo: <b>{cfg["llm"]["model"]}</b> via Ollama ({cfg["llm"]["host"]}) · '
            f'janela {cfg["ingestao"]["janela_dias"]} dias · top {cfg["fila"]["top_n"]} pedidos/rodada</div>',
            unsafe_allow_html=True,
        )

    if st.button("Gerar fila da rodada", key="rec_gerar"):
        with st.spinner("Rodando scoring + justificativa/mensagem + reflexão..."):
            try:
                st.session_state["rec_pacotes"] = planner.executar_rodada(vendas_full, data_ref, cfg)
                st.session_state.setdefault("rec_contatados", set())
            except OllamaIndisponivel as exc:
                st.session_state["rec_pacotes"] = []
                st.error(
                    f"Ollama não respondeu: {exc}\n\nRode `ollama serve` e confirme que o modelo "
                    f"`{cfg['llm']['model']}` foi baixado (`ollama pull {cfg['llm']['model']}`)."
                )

    pacotes = st.session_state.get("rec_pacotes")
    if pacotes is None:
        st.info("Escolha a data de referência e clique em 'Gerar fila da rodada'.")
        return
    if not pacotes:
        st.warning("Nenhum pedido elegível (pagamento aguardando/cancelado) dentro da janela para essa data de referência.")
        return

    st.session_state.setdefault("rec_contatados", set())
    veredito_kind = {"aprovado": "good", "ressalva": "warning", "rejeitado": "critical"}

    for i, pacote in enumerate(pacotes):
        pedido = pacote["pedido"]
        just, msg = pacote["justificativa"], pacote["mensagem"]
        ja_contatado = pedido["order_id"] in st.session_state["rec_contatados"]
        titulo = f"{pedido['order_id']} · {theme.fmt_brl(pedido['receita_liquida'])} · score {pedido['score']:.2f}"
        if ja_contatado:
            titulo += " · já contatado nesta rodada"

        with st.expander(titulo):
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown(theme.stat_tile("Status", pedido["status_pagamento"], f"{pedido['dias_parado']} dias parado", "neutral"), unsafe_allow_html=True)
            with cc2:
                st.markdown(theme.stat_tile("Forma de pagamento", pedido["metodo_pagamento"], pedido["canal"], "neutral"), unsafe_allow_html=True)

            st.markdown("**Justificativa executiva**")
            st.markdown(theme.alert_card(veredito_kind.get(just["veredito"], "info"), just["texto"] or "(sem texto — ver erro abaixo)"), unsafe_allow_html=True)
            st.caption(f"Reflexão: {just['veredito']} — {just['motivo']}")

            st.markdown("**Mensagem ao cliente (rascunho)**")
            st.markdown(theme.alert_card(veredito_kind.get(msg["veredito"], "info"), msg["texto"] or "(sem texto — ver erro abaixo)"), unsafe_allow_html=True)
            st.caption(f"Reflexão: {msg['veredito']} — {msg['motivo']}")

            if pacote["erro"]:
                st.error(pacote["erro"])

            b1, b2, b3, b4 = st.columns(4)
            acao = None
            if b1.button("Aprovar e enviar", key=f"rec_aprovar_{i}", disabled=ja_contatado):
                acao = "aprovado"
            if b2.button("Editar antes de enviar", key=f"rec_editar_{i}", disabled=ja_contatado):
                acao = "editar"
            if b3.button("Descartar", key=f"rec_descartar_{i}"):
                acao = "descartado"
            if b4.button("Adiar", key=f"rec_adiar_{i}"):
                acao = "adiado"

            if acao:
                registro.registrar(pacote, acao)
                if acao in ("aprovado", "editar"):
                    st.session_state["rec_contatados"].add(pedido["order_id"])
                st.success(f"Registrado: {acao}. Ver data/logs/execucoes.csv")
