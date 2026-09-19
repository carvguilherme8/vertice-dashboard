"""Identidade visual do Painel Único — estética de BI corporativo (azul neutro,
cinzas de sistema, cores de status reservadas), seguindo a paleta validada
(CVD-safe) descrita na skill dataviz/references/palette.md.
"""
import textwrap

import streamlit as st

# ---- paleta de dados (validada: CVD Delta E >= 8, contraste ok) ------------
CAT_BLUE = "#2a78d6"
CAT_ORANGE = "#eb6834"
CAT_AQUA = "#1baf7a"
CAT_YELLOW = "#eda100"
CAT_MAGENTA = "#e87ba4"
CAT_GREEN = "#008300"
CAT_VIOLET = "#4a3aa7"
CAT_RED = "#e34948"
CATEGORICAL = [CAT_BLUE, CAT_ORANGE, CAT_AQUA, CAT_YELLOW, CAT_MAGENTA, CAT_GREEN, CAT_VIOLET, CAT_RED]

# status (fixo, nunca reaproveitado como categórico)
GOOD = "#0ca30c"
WARNING = "#d68a00"  # passo mais escuro que o token puro (#fab219) para legibilidade em texto
CRITICAL = "#d03b3b"

# rampa sequencial (azul, claro->escuro) para 6 categorias ORDINAIS
ORDINAL_BLUE_6 = ["#86b6ef", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

# referência (2 barras): "declarado/base" vs "real/apurado"
REF_GRAY = "#a8a7a0"
ACTUAL_BLUE = CAT_BLUE

# ---- chrome de sistema (dashboard corporativo, não marca de marketing) ----
SIDEBAR_BG = "#0f172a"
SIDEBAR_BG_2 = "#16213a"
PAGE_BG = "#f4f5f7"
SURFACE = "#ffffff"
INK = "#111827"
INK_2 = "#4b5563"
MUTED = "#8a8f98"
GRID = "#e8e9ec"
BASELINE = "#d0d2d8"
BORDER = "rgba(17,24,39,.09)"

FONT_STACK = "Inter, -apple-system, 'Segoe UI', system-ui, sans-serif"
TITLE_FONT = dict(family=FONT_STACK, color=INK, size=14)
DATA_LABEL_FONT = dict(family=FONT_STACK, color=INK, size=11.5)
AXIS_TITLE_FONT = dict(family=FONT_STACK, color=INK_2, size=11.5)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family=FONT_STACK, color=INK_2, size=11.5),
    title_font=TITLE_FONT,
    margin=dict(l=10, r=10, t=40, b=10),
    hoverlabel=dict(bgcolor="white", font=dict(family=FONT_STACK, size=12, color=INK), bordercolor=GRID),
    xaxis=dict(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE, tickfont=dict(family=FONT_STACK, color=INK_2, size=11), title_font=AXIS_TITLE_FONT, automargin=True),
    yaxis=dict(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE, tickfont=dict(family=FONT_STACK, color=INK_2, size=11), title_font=AXIS_TITLE_FONT, automargin=True),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(family=FONT_STACK, color=INK_2, size=11)),
    bargap=0.32,
)


def style_fig(fig, **overrides):
    layout = {**PLOTLY_LAYOUT, **overrides}
    fig.update_layout(**layout)
    return fig


def inject_base_css():
    tint_blue = hex_to_rgba(CAT_BLUE, 0.08)
    css = f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
        html, body, [class*="css"] {{ font-family: {FONT_STACK}; }}
        .stApp {{ background-color: {PAGE_BG}; }}
        div.block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1400px; }}

        h1, h2, h3, h4 {{ letter-spacing: -0.01em; color: {INK}; font-weight: 700; }}
        p, li, label {{ color: {INK_2}; }}
        [data-testid="stCaptionContainer"] {{ color: {MUTED} !important; font-size: 12.5px; }}

        /* cabeçalho: título + filtros na mesma linha, no lugar da sidebar */
        .app-title h1 {{ font-size: 21px; margin: 6px 0 2px; line-height: 1.2; }}
        .app-title .sub {{ font-size: 12.5px; color: {MUTED}; }}
        .header-divider {{ border-bottom: 1px solid {BORDER}; margin: 2px 0 10px; }}

        /* KPI tiles */
        .stat-tile {{
            background: {SURFACE} !important; border: 1px solid {BORDER}; border-radius: 10px;
            padding: 10px 14px 9px; min-height: 92px; box-shadow: 0 1px 2px rgba(17,24,39,.04);
            display: flex; flex-direction: column; justify-content: space-between; overflow: hidden;
        }}
        .stat-tile .label {{ font-size: 10.5px; font-weight: 600; letter-spacing: .02em; text-transform: uppercase; color: {MUTED} !important; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .stat-tile .value {{ font-size: 20px; font-weight: 700; color: {INK} !important; line-height: 1.15; }}
        .stat-tile .delta {{ font-size: 11px; margin-top: 2px; color: {INK_2} !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .stat-tile .delta.good {{ color: {GOOD} !important; }} .stat-tile .delta.critical {{ color: {CRITICAL} !important; }} .stat-tile .delta.warning {{ color: {WARNING} !important; }}
        .stat-tile .spark {{ display:block; margin-top: 5px; width: 100%; height: 20px; }}
        .stat-tile .spark svg {{ display:block; width: 100%; height: 100%; }}

        /* indicador de status (substitui emoji) */
        .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:middle; }}

        /* cartão de alerta discreto (substitui st.error/warning/info padrão) */
        .alert-card {{
            flex: 1 1 240px; background:{SURFACE}; border:1px solid {BORDER}; border-left:3px solid var(--ac, {MUTED});
            border-radius: 8px; padding: 8px 12px; font-size: 12px; line-height: 1.35; color:{INK_2};
        }}
        .alert-card b {{ color:{INK}; }}
        .alert-card.critical {{ --ac: {CRITICAL}; }}
        .alert-card.warning {{ --ac: {WARNING}; }}
        .alert-card.info {{ --ac: {CAT_BLUE}; }}

        .section-title {{ font-size: 14px; font-weight: 700; color:{INK}; margin: 14px 0 1px; display:flex; align-items:center; gap:8px; }}
        .section-sub {{ font-size: 11.5px; color:{MUTED}; margin: 0 0 6px; }}

        /* barra de abas: pills numa cor só (azul do app), sem diferenciar por módulo.
           Seletores sem qualificador de tag (div/button) de propósito — o Streamlit
           trocou a biblioteca dos componentes de abas entre versões e a tag mudou. */
        [data-testid="stTabs"] {{ width: 100% !important; margin-top: 22px; }}
        [data-testid="stTabs"] [role="tablist"] {{ display: flex !important; width: 100% !important; gap: 6px; }}
        [data-testid="stTabs"] [data-testid="stTab"] {{
            flex: 1 1 0 !important; width: auto !important; justify-content: center; white-space: nowrap;
            font-weight: 600; font-size: 13px; color: {INK_2}; cursor: pointer;
            padding: 9px 14px 10px; border-radius: 8px; background: {SURFACE};
            border: 1px solid {BORDER}; border-bottom: 3px solid {BORDER};
            box-shadow: 0 1px 2px rgba(17,24,39,.05);
            transition: background .12s ease, color .12s ease, box-shadow .12s ease, transform .12s ease;
        }}
        [data-testid="stTabs"] [data-testid="stTab"]:hover {{
            background: {PAGE_BG}; color: {INK}; box-shadow: 0 3px 6px rgba(17,24,39,.10); transform: translateY(-1px);
        }}
        [data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {{
            color: {CAT_BLUE}; background: {tint_blue}; border-color: {CAT_BLUE};
            font-weight: 700; box-shadow: 0 3px 8px rgba(17,24,39,.14); transform: translateY(-1px);
        }}
        [data-testid="stTabsScrollLeft"], [data-testid="stTabsScrollRight"] {{ display: none; }}
        div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 8px; }}
        div[data-testid="stVerticalBlockBorderWrapper"] {{ margin-bottom: 0.3rem; }}
        div.element-container {{ margin-bottom: 0.35rem; }}

        /* moldura arredondada dos gráficos + bold em todo texto do SVG */
        div[data-testid="stPlotlyChart"] {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
            padding: 8px; overflow: hidden; box-shadow: 0 1px 2px rgba(17,24,39,.04);
        }}
        div[data-testid="stPlotlyChart"] svg text {{ font-weight: 700 !important; }}

        /* cartão do guia de abas (aba "Guia do painel") */
        div[data-testid="column"]:has(.guide-card) {{ display: flex; }}
        div[data-testid="column"]:has(.guide-card) > div {{ display: flex; flex-direction: column; width: 100%; }}
        div[data-testid="column"]:has(.guide-card) div.element-container:has(.guide-card) {{ flex: 1; display: flex; }}
        .guide-card {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-top: 6px solid {CAT_BLUE};
            border-radius: 10px; padding: 14px 16px 16px; margin-bottom: 8px; width: 100%; box-sizing: border-box;
            box-shadow: 0 1px 2px rgba(17,24,39,.04);
        }}
        .guide-card-head {{ display: flex; align-items: center; gap: 8px; margin-bottom: 9px; }}
        .guide-card-num {{
            display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
            width: 22px; height: 22px; border-radius: 50%; background: {CAT_BLUE};
            color: #fff; font-size: 11.5px; font-weight: 700;
        }}
        .guide-card-title {{ font-size: 15px; font-weight: 700; color: {INK}; }}
        .guide-card-label {{ font-size: 10.5px; font-weight: 600; letter-spacing: .02em; text-transform: uppercase; color: {MUTED}; margin: 10px 0 2px; }}
        .guide-card-label:first-of-type {{ margin-top: 0; }}
        .guide-card-text {{ font-size: 12.5px; line-height: 1.5; color: {INK_2}; }}
        </style>
        """
    # Colapsa para uma única linha, sem quebras: uma linha em branco no meio de
    # tags como <link> faz o Markdown encerrar o bloco HTML ali e tratar o
    # resto como texto solto (era a causa do CSS aparecendo cru na página).
    one_line = " ".join(line.strip() for line in css.splitlines() if line.strip())
    st.markdown(one_line, unsafe_allow_html=True)


def dot(color: str) -> str:
    return f'<span class="dot" style="background:{color};"></span>'


def sparkline_svg(values, color: str = CAT_BLUE) -> str:
    vw, vh = 200, 40
    vals = [float(v) for v in values if pd_notna(v)]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = (i / (n - 1)) * (vw - 6) + 3
        y = vh - 4 - ((v - lo) / span) * (vh - 8)
        pts.append(f"{x:.1f},{y:.1f}")
    last_x, last_y = pts[-1].split(",")
    return (
        f'<div class="spark"><svg viewBox="0 0 {vw} {vh}" preserveAspectRatio="none">'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.5" '
        f'vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="3" fill="{color}"/>'
        f"</svg></div>"
    )


def pd_notna(v) -> bool:
    try:
        return v is not None and v == v  # filtra None e NaN sem depender de pandas aqui
    except Exception:
        return False


def stat_tile(label: str, value: str, delta: str | None = None, delta_kind: str = "neutral", spark_values=None, spark_color: str = CAT_BLUE) -> str:
    delta_html = f'<div class="delta {delta_kind}">{delta}</div>' if delta else ""
    spark_html = sparkline_svg(spark_values, spark_color) if spark_values is not None else ""
    return (
        '<div class="stat-tile">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f"{delta_html}"
        f"{spark_html}"
        "</div>"
    )


def alert_card(kind: str, text: str) -> str:
    return f'<div class="alert-card {kind}">{text}</div>'


def guide_card(accent: str, numero: str, titulo: str, funcao: str, problema: str) -> str:
    bg = hex_to_rgba(accent, 0.07)
    return (
        f'<div class="guide-card" style="border-top-color:{accent};background-color:{bg};">'
        '<div class="guide-card-head">'
        f'<span class="guide-card-num" style="background-color:{accent};">{numero}</span>'
        f'<span class="guide-card-title">{titulo}</span>'
        "</div>"
        '<div class="guide-card-label">O que faz</div>'
        f'<div class="guide-card-text">{funcao}</div>'
        '<div class="guide-card-label">Problema de negócio que resolve</div>'
        f'<div class="guide-card-text">{problema}</div>'
        "</div>"
    )


def hex_to_rgba(hex_color: str, alpha: float = 0.08) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def fmt_brl(v: float, decimals: int = 0) -> str:
    if v is None:
        return "—"
    s = f"{v:,.{decimals}f}"
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {s}"


def fmt_pct(v: float, decimals: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.{decimals}f}%".replace(".", ",")


def fmt_num(v: float, decimals: int = 0) -> str:
    if v is None:
        return "—"
    s = f"{v:,.{decimals}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")
