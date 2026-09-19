# Painel Único de Decisão Comercial · Vértice

Dashboard Streamlit do case Vértice (bootcamp EloGroup): margem, desconto, estoque, devolução e o módulo de IA "Recuperação de receita pós-venda".

## Abas

- **Recuperação de receita pós-venda** — fila priorizada de pedidos com pagamento pendente/cancelado (scoring determinístico + justificativa e mensagem geradas por LLM local via Ollama, com reflexão de passe único antes de qualquer texto chegar ao operador).
- **Prevenção de devolução na origem** — devolução por motivo (endereçável vs. decisão do cliente), por fornecedor e por SKU.
- **Priorizador de margem e receita** — guardrail de teto de desconto (margem) e reposição de SKUs críticos (receita em risco por ruptura).
- **Memo executivo** — relatório Fato/Causa/Implicação/Recomendação gerado a partir dos KPIs, com download em `.md`.

## Rodando localmente

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

A aba "Recuperação de receita pós-venda" precisa de [Ollama](https://ollama.com) rodando localmente com um modelo Gemma baixado:

```bash
ollama pull gemma3:4b   # ou outro tamanho — ajuste em dashboard/config/recuperacao.yaml
```

## ⚠️ Limitação no deploy em nuvem (Streamlit Community Cloud)

O Streamlit Community Cloud **não tem Ollama instalado** e não acessa o Ollama da sua máquina local — não há como uma aba hospedada na nuvem chamar um modelo que só existe no seu computador. Ao publicar este app lá, as abas **Prevenção de devolução**, **Priorizador de margem e receita** e **Memo executivo** funcionam normalmente (são só pandas/plotly), mas a aba **Recuperação de receita pós-venda** vai mostrar o erro tratado "Ollama não respondeu" ao clicar em "Gerar fila da rodada" — a fila priorizada (scoring) é calculada, só a geração de texto por LLM não roda lá. Para essa aba funcionar 100% em produção seria necessário trocar o backend de Ollama local para uma API hospedada (ex.: Anthropic Claude, ver discussão no histórico do case) ou hospedar o Ollama em outro serviço acessível pela internet.

## Testes

```bash
pytest tests/ -v
python scripts/backtest_rodadas.py --inicio 2023-06-01 --fim 2024-01-26 --step 7
```

## Estrutura

```
dashboard/          # app Streamlit
  src/              # dados, métricas, tema, módulo de recuperação de receita
  views/            # painel.py — as 4 abas
  config/           # recuperacao.yaml (pesos, política, modelo LLM)
  prompts/          # templates de prompt (justificativa, mensagem, reflexão)
data/processed/     # parquet já limpo (vendas, clientes, estoque, atendimento, marketing)
tests/              # pytest — ingestão e scoring são puros, sem depender do Ollama
scripts/            # backtest_rodadas.py — replay de datas históricas sem dado novo
```
