# ADR 0004 — JSONB Canônico de Atributos

## Status
Aceito (v2.3.0)

## Decisão
`variantes.atributos` (JSONB) é a fonte canônica dos atributos técnicos.
O EAV legado (`variante_atributos`) fica congelado somente-leitura nesta
release; DROP físico apenas em Contract futuro. Atributos flexíveis não
substituem colunas estruturais de integridade/pesquisa/auditoria/cálculo.
