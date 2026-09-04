# PROBLEM
- **Severidade:** média
- **Categoria:** incoerência
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `frontend/src/ui/ui.tsx:134-224`, `frontend/src/pages/pre-venda.tsx:875-932`, `frontend/src/pages/compras.tsx:856-900`, `frontend/src/pages/cotacoes/compare-table.tsx:64-100`, `frontend/src/pages/perfis.tsx:192-230`

## Explicação para leigos
O projeto define um componente de tabela compartilhado, mas telas críticas criam grades próprias. Isso faz com que recursos de acessibilidade, responsividade, ordenação e navegação por teclado funcionem de maneira diferente em cada módulo.

## Evidência e análise técnica
O componente `Table` injeta `data-label` para mobile e `THead` declara `scope`/`aria-sort`. A lista de itens da pré-venda não é uma tabela nativa: usa cabeçalho de `div` e linhas com `role="group"`. Matrizes de compras, comparação de cotações e matriz de perfis usam `<table>` locais, sem o contrato comum, e alguns não definem `scope="col"`, ordenação acessível ou modelo de foco de grid. O `AGENTS.md` estabelece alinhamento com Salesforce Lightning Datatable/SLDS para tabelas e navegação por teclado.

## Impacto
Operadores que trabalham somente com teclado encontram comportamentos inconsistentes entre telas. Leitores de tela podem não anunciar linhas/células como esperado, e mudanças futuras de layout podem corrigir uma tela e quebrar outra. Em matrizes largas, a falta de um padrão único piora a navegação e a leitura de contexto.

## Solução proposta
Definir primitives de tabela/grid com contrato explícito: semântica nativa quando a operação é tabular, `role="grid"` somente quando há navegação ativa por setas, roving tabindex, `aria-rowindex`/`aria-colindex`, seleção, ordenação e ação de linha. Migrar as telas críticas para essas primitives, documentar exceções e cobrir Enter, Espaço, setas, Home/End, Delete e foco visível nos testes.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ pre-venda.tsx
-<div role="group" tabIndex={0} ...>
+<div role="grid" aria-label="Itens da pré-venda">
+  <div role="row" aria-rowindex={index + 2} ...>
+    <div role="gridcell" aria-colindex={1}>...</div>
+  </div>
+</div>
```

