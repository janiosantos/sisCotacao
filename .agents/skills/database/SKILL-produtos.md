---
name: database
description: Modelar banco, migrations, índices, constraints, backfills e preservação de histórico para o domínio fiscal e comercial. Usar em alterações de schema ou persistência.
---

# Database

Projetar primeiro o modelo e suas invariantes. Separar Product, ProductVariant, TaxRule, IBPTTable e InvoiceItem. Versionar TaxRule e tabelas externas por vigência.

Antes de executar migration, verificar volume, locks, compatibilidade de leitura/escrita, rollback e integridade. Após executar, validar contagens, índices, constraints e amostras anonimizadas.
