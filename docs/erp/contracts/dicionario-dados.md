# Dicionário de dados e contratos — ERP Casa LM

> **GOV-002 do plano mestre.** Padroniza nomes, unidades, status, datas, dinheiro,
> percentuais, identificadores, códigos de erro e paginação. Todo endpoint novo
> segue estas convenções; o OpenAPI (`backend/openapi.json`) é o contrato de
> request/response.

## 1. Campos comuns (onde aplicável)

| Campo | Tipo | Regra |
|---|---|---|
| `id` | int (PK) | Nunca reaproveitar ID; nunca expor sequência como verdade de negócio |
| `empresa_id` / `filial_id` | int | Só quando multiempresa/multifilial aprovado (MDM-001); hoje não existe escopo — **não simular isolamento** |
| `deposito_id` | int | Obrigatório em saldo/movimento/parâmetros de estoque |
| `criado_em` / `atualizado_em` | timestamp (UTC) | Timestamp ISO 8601 UTC; exibição em fuso local só no frontend |
| `versao` | int | Para documentos versionados (pedido, regra, política, conversão) |
| `correlation_id` | string | Idempotência/rastreio em operações que geram efeito (postagem, emissão, cobrança, job); no header `X-Correlation-Id` e no corpo do erro |

## 2. Identificadores de produto

- **EAN/GTIN**: somente dígitos, validado quando aplicável; múltiplos por produto
  via `produto_identificador` (MDM-003); unicidade por contexto; busca exata antes da textual.
- **SKU/código interno**: único; produto sem GTIN pode usar código interno **sem inventar GTIN**.
- **Código do fornecedor**: vinculado ao fornecedor; resolve para produto/embalagem no recebimento.

## 3. Unidades e valores

- **Unidades**: `UN, CX, PCT, RL, M, KG, L` (sem plural); tabela de conversão
  versionada por produto/embalagem (MDM-002); unidade base para estoque; venda/compra/
  tributável exibem a unidade correta.
- **Dinheiro**: centavos como `numeric(14,2)` no banco; `number` (não `string`) na API;
  formatação BRL só no frontend (`fmtMoney`).
- **Percentual**: `numeric(5,2)` (ex.: `5.25` = 5,25%); nunca como `0.0525`.
- **Datas**: `YYYY-MM-DD` para datas de negócio; `ISO 8601` com fuso para timestamps.

## 4. Status

- Status são **códigos estáveis em snake_case** (ex.: `finalizado`, `em_analise`,
  `parcialmente_recebido`); o rótulo de exibição é responsabilidade do frontend.
- Transições **não** são feitas por `PATCH` livre de status em documentos críticos —
  ver `contracts/maquinas-estado.md`.

## 5. Erros (contrato estável)

```json
{ "error": "mensagem amigável", "code": "sem_estoque", "details": {...}, "correlation_id": "..." }
```

- `error`: humano, sem stack trace/segredo.
- `code`: snake_case, estável, documentado no OpenAPI.
- `details`: estrutura opcional por domínio.
- `correlation_id`: obrigatório em operações de efeito; registrado no log.
- Status HTTP: `400` entrada, `401` não autenticado, `403` não autorizado (RBAC),
  `404` ausente, `409` conflito/estado, `422` domínio, `429` rate limit, `500` interno.

## 6. Paginação e listas

- Listas: `?pagina=`/`?por_pagina=` (ou `offset`/`limit` com `has_more` quando já estabelecido na API pública).
- `por_pagina` com teto (ex.: 100); backend valida e capa; respostas incluem total quando necessário.
- Filtros: parâmetros de query nomeados e validados; nunca concatenar SQL sem bind.
- Listas grandes: paginação/virtualização no frontend (não carregar milhares de registros).

## 7. Regras para novas APIs

1. Não retornar campos internos (custo, fornecedores, classe_abc, NCM) em APIs públicas sem decisão.
2. Request/response documentados no OpenAPI; tipos TypeScript gerados/espelhados (sem `any` no contrato).
3. Backend valida payload (enum/status, limites, decimal, datas, ids) e rejeita campos desconhecidos quando seguro.
4. Autoria e auditoria usam o sujeito Bearer (`request.usuario.sub`), não só sessão.
5. Chaves de idempotência (`X-Idempotency-Key` ou campo dedicado) em criação de pedido, recebimento, emissão, cobrança, devolução, importação e jobs (ARC-003).