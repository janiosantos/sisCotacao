# SKILL — Banco de Dados

## Objetivo

Padronizar evolução e integridade do PostgreSQL.

## Regras

- PostgreSQL é o banco de produção.
- Usar NUMERIC para dinheiro e tributos.
- Usar TIMESTAMPTZ para eventos que exigem instante absoluto.
- Usar DATE para vigência de regras quando apropriado.
- Utilizar UUID ou chaves consistentes com a arquitetura.
- Criar constraints e foreign keys.
- Criar índices orientados às consultas reais.

## Migrations

Fluxo:

modelo
→ migration
→ teste
→ compatibilidade
→ deploy

Evitar migrations destrutivas.

## Histórico

Dados fiscais, financeiros e documentos autorizados devem permanecer preservados.

## Versionamento fiscal

Regras devem permitir identificar:

- versão;
- vigência;
- fundamento;
- status.

## Performance

Evitar N+1 queries. Índices devem acompanhar campos usados pelo motor fiscal e consultas críticas.

## Concorrência

Usar transações, locks ou mecanismos apropriados para:

- estoque;
- documentos;
- numeração;
- operações financeiras.
