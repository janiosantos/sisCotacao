# SKILL — Backend/API

## Responsabilidade

O backend é a autoridade de negócio.

Responsabilidades:

- validações;
- regras de domínio;
- cálculos;
- persistência;
- auditoria;
- integrações;
- emissão fiscal.

## Arquitetura

Preferir separação:

- domain;
- application;
- infrastructure;
- presentation.

O domínio fiscal não deve depender diretamente de HTTP, HTML ou framework.

## API

Contratos devem ser claros.

Erros devem conter:

- código;
- mensagem;
- contexto;
- detalhes seguros.

## Fiscal

O frontend envia contexto comercial. O backend resolve a tributação.

Não aceitar do frontend um ICMS calculado como fonte de verdade.

## Idempotência

Operações de emissão e eventos externos devem possuir proteção contra duplicidade quando aplicável.
