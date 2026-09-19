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
