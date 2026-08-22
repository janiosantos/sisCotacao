# Regra de Banco de Dados

Usar migrations versionadas, reversíveis quando possível e seguras para execução repetida. Não apagar ou sobrescrever dados históricos de documentos fiscais emitidos.

## Requisitos de modelagem

- Usar chaves estáveis e timestamps de auditoria.
- Criar índices para NCM, vigência, regime, operação e UFs quando usados na resolução.
- Impor unicidade apenas quando o domínio garantir a regra; não presumir que um NCM tenha uma única parametrização.
- Modelar `variant_id` como opcional em TaxRule para permitir herança Produto → Variação.
- Guardar snapshots dos resultados em InvoiceItem, sem depender da regra atual para reconstituir notas antigas.
- Evitar JSONB para dados que precisem de filtros fiscais críticos; reservar JSONB para atributos técnicos flexíveis.

Toda migration deve incluir plano de backfill, compatibilidade, rollback e verificação pós-execução.
