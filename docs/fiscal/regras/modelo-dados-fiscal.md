# Modelo Fiscal — Estrutura Conceitual

## Classificação

```text
ncm
ncm_version
cest
cest_version
fiscal_product_classification
```

## Regras

```text
fiscal_rule
fiscal_rule_version
fiscal_rule_condition
fiscal_rule_result
fiscal_rule_legal_reference
```

## Operação e resultado

```text
fiscal_operation_type
fiscal_operation_context
fiscal_result
fiscal_snapshot
```

## Documento

```text
fiscal_document
fiscal_document_item
fiscal_document_event
fiscal_document_xml
```

## Regra

```text
fiscal_rule
  id
  code
  name
  type
  priority
  status

fiscal_rule_version
  id
  rule_id
  version
  valid_from
  valid_to
  source_url
  legal_reference

fiscal_rule_condition
  rule_version_id
  field
  operator
  value

fiscal_rule_result
  rule_version_id
  cfop
  cst
  csosn
  icms_rule
  st_rule
  difal_rule
  fcp_rule
```

A implementação real deve ser adaptada à arquitetura e às necessidades de consulta/performance.
