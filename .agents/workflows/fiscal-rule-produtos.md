# Workflow: Nova Regra Fiscal

## Objetivo
Adicionar ou alterar uma regra fiscal sem misturar parametrização com resultado histórico.

## Etapas

1. Descrever o cenário e o efeito esperado.
2. Identificar fontes e registrar a vigência.
3. Definir chave de contexto e precedência.
4. Modelar TaxRule/FiscalProfile e eventual override.
5. Implementar resolução e mensagens de pendência.
6. Criar testes de cenário, conflito e regressão.
7. Simular contra dados anonimizados.
8. Obter revisão fiscal e técnica.
9. Publicar com vigência explícita e monitorar.
10. Registar decisão em `docs/fiscal/decisoes/`.

**Gate:** sem fonte ou aprovação, manter `A CONFIRMAR` e não publicar.
