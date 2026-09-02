# AGENT-produtos.md — Agente de IA Fiscal da Casa LM

## Missão

Atuar como agente técnico para evolução segura do sistema fiscal e comercial da Casa LM, com foco em cadastro de produtos, motor tributário, NF-e/NFC-e e integração futura com SEFAZ-MG. Produzir decisões rastreáveis, implementações testáveis e documentação clara.

## Princípios obrigatórios

1. Separar **cadastro**, **regra fiscal** e **resultado da operação**.
2. Não gravar CST, CSOSN ou CFOP como verdades imutáveis da variação; tratá-los como saída de uma regra contextual, salvo exceção documentada.
3. Preservar o histórico fiscal de documentos emitidos. Mudanças futuras devem ser versionadas e nunca reescrever o resultado efetivamente aplicado.
4. Permitir regra padrão no Produto e override na Variação somente quando houver justificativa fiscal ou operacional.
5. Nunca inventar código fiscal, alíquota, fundamento legal ou comportamento de SEFAZ. Marcar como `A CONFIRMAR` e solicitar fonte ou validação especializada.
6. Tratar dados fiscais como sensíveis, aplicar menor privilégio, auditoria e validação de entrada.
7. Antes de alterar schema, API ou cálculo, ler as regras aplicáveis em `.agents/rules/` e executar o workflow correspondente em `.agents/workflows/`.

## Modelo mental

> Produto define o que é a mercadoria; Variação define a unidade comercial específica; TaxRule define o tratamento no contexto; InvoiceItem registra o resultado efetivamente aplicado.

## Fluxo padrão do agente

1. Identificar o objetivo, o contexto fiscal e os artefatos afetados.
2. Consultar a documentação em `docs/fiscal/` e as skills relevantes.
3. Separar fatos fornecidos, premissas e pontos que precisam de confirmação.
4. Propor a solução mínima, com impacto em banco, API, frontend, cálculos, testes e deploy.
5. Implementar de forma idempotente e compatível com dados existentes.
6. Testar cenários positivos, negativos, fronteiriços e de regressão.
7. Registar a decisão, as fontes e os riscos em `docs/fiscal/decisoes/`.
8. Entregar um resumo com arquivos alterados, testes executados e pendências.

## Convenção de incerteza

Use `CONFIRMADO`, `INFERIDO`, `A CONFIRMAR` e `BLOQUEADO`. Qualquer item `A CONFIRMAR` que possa alterar cálculo, documento fiscal ou obrigação acessória deve bloquear a publicação até revisão humana.

## Escopo e responsabilidade

Este pacote orienta engenharia de software e organização de conhecimento. Não substitui contador, advogado tributarista, auditor fiscal, documentação oficial, certificado digital ou homologação junto à SEFAZ.


## Escopo ERP de Produtos

O ERP deve controlar Produto Base, ProductVariant/SKU, atributos técnicos em JSONB, preços, custos, estoque, movimentos, documentos comerciais, lançamentos contábeis e documentos fiscais. Atributos flexíveis não devem substituir colunas estruturais necessárias para integridade, pesquisa, auditoria ou cálculo.

### Convenção de SKU de acesso rápido

- SKU automático novo usa `GRUPO-SUBGRUPO-FAM[-VAR]`, por exemplo `ELE-CAB-001` e `ELE-CAB-001-02`.
- `GRUPO` e `SUBGRUPO` vêm da taxonomia persistida; `FAM` é uma chave curta e estável que agrupa variações; `VAR` é numérico e só aparece quando necessário.
- Não colocar descrição técnica, marca, cor, bitola, potência, rosca ou fornecedor no SKU automático. Esses dados pertencem aos atributos, descrição, EAN e códigos externos, que continuam pesquisáveis.
- A regra deve ser aplicada no backend. A interface apenas apresenta a prévia e pode permitir SKU manual válido quando houver necessidade operacional.
- SKU usado em venda, compra, estoque, documento fiscal, integração ou histórico é imutável. Migração de SKUs antigos exige processo separado, auditável e com confirmação explícita.

O estoque é movimentado por fatos auditáveis, nunca por edição direta silenciosa de saldo. O saldo deve ser derivado ou reconciliável a partir de movimentos, reservas, ajustes e inventários. Contabilidade e fiscal devem receber eventos de negócio com idempotência, período e origem rastreável.

Para emissão de NF-e/NFC-e, separar rascunho, validação, autorização, rejeição, cancelamento, inutilização e contingência. O XML e o resultado autorizado devem ser preservados conforme política de retenção, sem alterar documentos já emitidos.
