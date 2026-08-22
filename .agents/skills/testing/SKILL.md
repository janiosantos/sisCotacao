# SKILL — Testes

## Obrigatório

Toda alteração relevante deve possuir testes.

## Fiscal

Testar:

- regra;
- cálculo;
- vigência;
- prioridade;
- conflito;
- ausência de regra;
- arredondamento;
- regressão;
- snapshot;
- cenários internos;
- cenários interestaduais;
- devoluções quando aplicável.

## Golden Tests

Manter entradas e resultados esperados para cenários fiscais críticos.

## Regressão

Alteração de regra deve preservar testes históricos.

## Integração

Quando aplicável, testar:

- XML;
- schema;
- adapter SEFAZ;
- autorização em homologação;
- persistência do resultado.

## Falha

Testes não devem ser removidos apenas para fazer o pipeline passar. Se uma regra mudou, atualizar o teste com justificativa documentada.
