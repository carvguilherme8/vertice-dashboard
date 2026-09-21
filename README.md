# Painel Único de Decisão Comercial · Vértice

### Aplicações em Produção

-  **Solução Proposta (Painel Único · Streamlit):** [case-vertice-dashboard.streamlit.app/](https://case-vertice-solution.streamlit.app/)
-  **Dashboard de Gestão (Dash · Plotly Cloud):** [vertice-dashboard-gestao.plotly.app](https://vertice-dashboard-gestao.plotly.app/)

---

Dois entregáveis do case Vértice (bootcamp EloGroup), cada um com seu propósito:

- **`solucao_final/`** (Streamlit) — o Painel Único: ferramenta de ação (recuperação de receita com IA, guardrails, memo executivo). Este é o app com abas, descrito abaixo.
- **`dash_gestao/`** (Dash) — o Dashboard de Gestão: só leitura, indicadores-chave para a diretoria acompanhar margem, canais, clientes, operação e atendimento. Sem IA, sem botão que dispare ação — ver seção própria abaixo.

## Abas (Painel Único · Streamlit)

- **Recuperação de receita pós-venda** — fila priorizada de pedidos com pagamento pendente/cancelado (scoring determinístico + justificativa e mensagem geradas por LLM, com reflexão de passe único antes de qualquer texto chegar ao operador). Provedor de LLM plugável: API Sandbox EloAgents (padrão) ou Ollama local — ver `solucao_final/config/recuperacao.yaml`.
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
pip install -r solucao_final/requirements.txt
streamlit run solucao_final/app.py
```

A aba "Recuperação de receita pós-venda" precisa de um provedor de LLM configurado em `solucao_final/config/recuperacao.yaml` (`llm.provider`):

- **`eloagents`** (padrão) — API Sandbox da EloGroup, mesmo endpoint/modelo usados na `Aula07_Pratica.ipynb`. Copie `solucao_final/.streamlit/secrets.toml.example` para `solucao_final/.streamlit/secrets.toml` e preencha `ELOAGENTS_API_KEY` (esse arquivo nunca é versionado). No deploy, a mesma chave vai em "Manage app" → "Settings" → "Secrets" do Streamlit Cloud.
- **`ollama`** — modelo local, sem custo e sem dado saindo do ambiente:
  ```bash
  ollama pull gemma3:4b   # ou outro tamanho — ajuste model/host em recuperacao.yaml
  ```

## Testes

```bash
pytest tests/ -v
python scripts/backtest_rodadas.py --inicio 2023-06-01 --fim 2024-01-26 --step 7
```

## Notebooks de Análise

`notebooks_analises/` documenta o diagnóstico exploratório que sustenta os dois apps — é o processo que gerou `data/processed/` e as hipóteses por trás dos KPIs. Pensados pra rodar em sequência (01→08, no mesmo kernel):

1. **`01_qualidade_dados.ipynb`** — audita as 5 bases do data room (nulos, duplicidade, integridade referencial, cobertura temporal, consistência de fórmulas) e exporta a versão tratada pra `data/processed/*.parquet`.
2. **`02_analise_exploratoria.ipynb`** — visualiza as relações entre as métricas e o problema central do case (queda de rentabilidade com volume crescendo), uma seção por linha de investigação (Margem, Marketing, Operações, Atendimento, Cliente).
3. **`03_testes_estatisticos.ipynb`** — formaliza os padrões do notebook 02 em teste de hipótese, p-valor e tamanho de efeito.
4. **`04_hipoteses_para_apresentacao.ipynb`** — reúne só as hipóteses com suporte estatístico real (confirmadas ou refutadas), cada uma com o gráfico e o teste que a sustentam — material-fonte dos slides.
5. **`05_sanity_check.ipynb`** — papel de revisor cético: recomputa os números mais citados do zero, com código independente, e confronta contra os notebooks 06 e 07.
6. **`06_numeros_canonicos.ipynb`** — fonte única de verdade dos números do diagnóstico; qualquer valor citado em outro lugar (05, 07, dashboards) tem que vir daqui.
7. **`07_avaliacao_impacto.ipynb`** — calcula o impacto financeiro de cada frente a partir dos números canônicos do 06 — base das métricas mostradas nos dois apps.
8. **`08_priorizacao_e_selecao.ipynb`** — decide onde atuar primeiro e qual solução construir, com a priorização como saída do cálculo, não premissa de entrada.

**Reprodutibilidade:** só o `01` e o `02` rodam com o que já está no repo (`data/processed/`). Os demais dependem de artefatos deliberadamente fora do controle de versão — `01`, `05` e `06` precisam dos CSVs brutos do data room e `07`/`08` consomem os `.json` que `05`/`06` gravam em `outputs/` (também gitignored). Os notebooks continuam servindo como documentação do raciocínio, só não re-executam do zero.

## Dashboard de Gestão (Dash)

Painel de leitura para a diretoria — 6 seções (Visão Geral, Margem, Canais, Clientes, Operação, Atendimento), cada uma com KPIs e gráficos que reaproveitam as mesmas fórmulas validadas do Painel Único (`solucao_final/src/metrics.py`), então os números nunca divergem entre os dois apps. Filtros de período, canal e categoria no topo; a seção Canais sempre mostra todos os canais (filtrar por canal ali anularia a própria comparação), e Clientes/Atendimento são fotografias completas da base (sem cruzamento de data com vendas).

```bash
pip install -r requirements.txt   # requirements da raiz — dash_gestao/app.py reaproveita solucao_final/src/
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
solucao_final/      # app Streamlit — Painel Único (ação)
  src/              # dados, métricas, tema, módulo de recuperação de receita
  views/            # painel.py — as 4 abas
  config/           # recuperacao.yaml (pesos, política, modelo LLM)
  prompts/          # templates de prompt (justificativa, mensagem, reflexão)
dash_gestao/         # app Dash — Dashboard de Gestão (leitura)
  app.py            # layout + callback únicos; reaproveita solucao_final/src/metrics.py e theme.py
  assets/style.css   # mesma identidade visual do Painel Único
data/processed/     # parquet já limpo (vendas, clientes, estoque, atendimento, marketing)
notebooks_analises/ # notebooks 01-08 do diagnóstico exploratório que gerou data/processed/
tests/              # pytest — ingestão e scoring são puros, sem depender do Ollama
scripts/            # backtest_rodadas.py — replay de datas históricas sem dado novo
```
