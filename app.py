"""Shim de entrypoint pra Plotly Cloud.

O app de verdade vive em dash_gestao/app.py — reaproveita solucao_final/src/
metrics.py e theme.py, por isso o deploy publica o repo inteiro, não só a
pasta dash_gestao/. Este arquivo existe só porque o Plotly Cloud exige um
.py na raiz do pacote publicado; --entrypoint-module já aponta pra
dash_gestao.app, mas reexportar aqui também garante que funcione se a
plataforma cair no fallback de raiz.
"""
from dash_gestao.app import app, server  # noqa: F401
