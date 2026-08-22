# Regras de Arquitetura

## Princípios

- Separar domínio, aplicação, infraestrutura e apresentação.
- Evitar acoplamento do domínio a framework.
- Separar módulos por responsabilidade.
- Preferir composição e interfaces a dependências rígidas.
- Não duplicar regras de negócio entre backend e frontend.
- Não criar dependências circulares.
- Toda integração externa deve ser isolada por adapter/service.

## Módulos conceituais

- products
- inventory
- sales
- purchases
- pricing
- fiscal
- finance
- customers
- suppliers
- documents
- integrations

## Fiscal

Fluxo conceitual:

Produto + Contexto + Legislação vigente
→ Motor Fiscal
→ Resultado Fiscal
→ Documento
→ Histórico/Auditoria

Produto não deve determinar sozinho CFOP, CST/CSOSN ou ICMS-ST.
