# Painel Único de Decisão Comercial · Vértice

### Aplicações em Produção

-  **Solução Proposta (Painel Único · Streamlit):** [case-vertice-dashboard.streamlit.app](https://case-vertice-dashboard.streamlit.app/)
-  **Dashboard de Gestão (Dash · Plotly Cloud):** [vertice-dashboard-gestao.plotly.app](https://vertice-dashboard-gestao.plotly.app/)

---

Dois entregáveis do case Vértice (bootcamp EloGroup), cada um com seu propósito:

- **`dashboard/`** (Streamlit), o Painel Único: ferramenta de ação (recuperação de receita com IA, guardrails, memo executivo). Este é o app com abas, descrito abaixo.
- **`dash_gestao/`** (Dash)m o Dashboard de Gestão: só leitura, indicadores-chave para a diretoria acompanhar margem, canais, clientes, operação e atendimento. Ver seção própria abaixo.

## Abas (Painel Único · Streamlit)

- **Recuperação de receita pós-venda** — fila priorizada de pedidos com pagamento pendente/cancelado (scoring determinístico + justificativa e mensagem geradas por LLM, com reflexão de passe único antes de qualquer texto chegar ao operador). Provedor de LLM plugável: API Sandbox EloAgents (padrão) ou Ollama local — ver `dashboard/config/recuperacao.yaml`.
- **Prevenção de devolução na origem** — devolução por motivo (endereçável vs. decisão do cliente), por fornecedor e por SKU.
- **Priorizador de margem e receita** — guardrail de teto de desconto (margem) e reposição de SKUs críticos (receita em risco por ruptura).
- **Memo executivo** — relatório Fato/Causa/Implicação/Recomendação gerado a partir dos KPIs, com download em `.md`.

## Requisitos

Python 3.11 ou 3.12. Evite 3.13+ por enquanto — algumas dependências transitivas (ex. `pydantic-core`, via `pydantic`/`litellm`) ainda não têm wheel pronta pra versões muito novas do Python, e o `pip install` cai numa compilação a partir do código-fonte que exige Rust/Cargo instalado na máquina.

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
```

## Rodando localmente

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

A aba "Recuperação de receita pós-venda" precisa de um provedor de LLM configurado em `dashboard/config/recuperacao.yaml` (`llm.provider`):

- **`eloagents`** (padrão) — API Sandbox da EloGroup, mesmo endpoint/modelo usados na `Aula07_Pratica.ipynb`. Copie `dashboard/.streamlit/secrets.toml.example` para `dashboard/.streamlit/secrets.toml` e preencha `ELOAGENTS_API_KEY` (esse arquivo nunca é versionado). No deploy, a mesma chave vai em "Manage app" → "Settings" → "Secrets" do Streamlit Cloud.
- **`ollama`** — modelo local, sem custo e sem dado saindo do ambiente:
  ```bash
  ollama pull gemma3:4b   # ou outro tamanho — ajuste model/host em recuperacao.yaml
  ```

## Testes

```bash
pytest tests/ -v
python scripts/backtest_rodadas.py --inicio 2023-06-01 --fim 2024-01-26 --step 7
```

## Dashboard de Gestão (Dash)

Painel de leitura para a diretoria — 6 seções (Visão Geral, Margem, Canais, Clientes, Operação, Atendimento), cada uma com KPIs e gráficos que reaproveitam as mesmas fórmulas validadas do Painel Único (`dashboard/src/metrics.py`), então os números nunca divergem entre os dois apps. Filtros de período, canal e categoria no topo; a seção Canais sempre mostra todos os canais (filtrar por canal ali anularia a própria comparação), e Clientes/Atendimento são fotografias completas da base (sem cruzamento de data com vendas).

```bash
pip install -r requirements.txt   # requirements da raiz — dash_gestao/app.py reaproveita dashboard/src/
python dash_gestao/app.py   # http://127.0.0.1:8060
```

Publicado no Plotly Cloud (privado — `app.py` na raiz é o shim de entrypoint que o deploy usa; `plotly-cloud.toml` guarda o app_id, mantenha versionado):

```bash
plotly app publish --project-path .
```

## Estrutura

```
app.py              # shim de entrypoint pro deploy no Plotly Cloud — reexporta dash_gestao/app.py
requirements.txt    # deps do deploy (raiz, não da pasta dash_gestao/ — ver comentário no arquivo)
plotly-cloud.toml   # app_id do deploy — versionado de propósito, sem segredo
dashboard/          # app Streamlit — Painel Único (ação)
  src/              # dados, métricas, tema, módulo de recuperação de receita
  views/            # painel.py — as 4 abas
  config/           # recuperacao.yaml (pesos, política, modelo LLM)
  prompts/          # templates de prompt (justificativa, mensagem, reflexão)
dash_gestao/         # app Dash — Dashboard de Gestão (leitura)
  app.py            # layout + callback únicos; reaproveita dashboard/src/metrics.py e theme.py
  assets/style.css   # mesma identidade visual do Painel Único
data/processed/     # parquet já limpo (vendas, clientes, estoque, atendimento, marketing)
tests/              # pytest — ingestão e scoring são puros, sem depender do Ollama
scripts/            # backtest_rodadas.py — replay de datas históricas sem dado novo
```
