# SKILL — Motor Fiscal

## Objetivo

Definir como implementar o motor fiscal de forma modular, testável, versionada e auditável.

## Arquitetura

Conceito:

FiscalContext
+
FiscalProduct
+
FiscalRules
+
OperationDate
→ FiscalEngine
→ TaxResult

## FiscalContext

Deve representar, conforme necessidade:

- regime tributário;
- UF origem;
- UF destino;
- tipo de operação;
- finalidade;
- consumidor final;
- contribuinte ICMS;
- modalidade do documento;
- data da operação.

## FiscalProduct

Deve fornecer dados fiscais do produto:

- NCM;
- CEST;
- origem;
- atributos necessários ao enquadramento.

## Componentes

Separar responsabilidades:

- ICMS Engine;
- ICMS-ST Engine;
- DIFAL Engine;
- FCP Engine;
- CFOP Resolver;
- CST/CSOSN Resolver.

Um orquestrador pode combinar os resultados.

## Regras

Preferir:

Rule
→ Conditions
→ Results

Cada regra deve possuir:

- ID;
- versão;
- prioridade;
- vigência;
- condições;
- resultados;
- fundamento legal.

## Prioridade

Regras específicas devem ter maior prioridade que regras genéricas.

Se houver conflito de mesma prioridade:

`FISCAL_RULE_CONFLICT`

## Resultado

O resultado deve ser estruturado e explicar o cálculo.

Campos conceituais:

- CFOP;
- CST/CSOSN;
- ICMS;
- ICMS-ST;
- DIFAL;
- FCP;
- rule_id;
- rule_version;
- legal_reference;
- matched_conditions;
- status.

## Estados

Usar estados explícitos, por exemplo:

- CALCULATED;
- FISCAL_REVIEW_REQUIRED;
- RULE_NOT_FOUND;
- RULE_CONFLICT;
- INVALID_PRODUCT_FISCAL_DATA;
- INVALID_OPERATION_CONTEXT;
- LEGISLATION_OUTDATED;
- CALCULATION_ERROR.

## Precisão

Usar Decimal no backend e NUMERIC no PostgreSQL.

Definir política de arredondamento explicitamente.

## Snapshot

Após a emissão/autorização, persistir o resultado fiscal efetivamente utilizado.

O histórico não deve depender da regra atualmente vigente.

## Proibições

Não:

- espalhar if/else fiscais;
- hardcodar alíquotas;
- recalcular documentos históricos com regras novas;
- permitir frontend decidir imposto;
- esconder ausência de regra retornando valores zero ou null sem status.
