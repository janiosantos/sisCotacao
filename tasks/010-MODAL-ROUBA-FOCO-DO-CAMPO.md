# PROBLEM
- **Severidade:** média
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `frontend/src/ui/ui.tsx:398-430`, `frontend/src/pages/orcamentos/modal-autorizar.tsx:55-73`, `frontend/src/pages/pre-venda/modal-autorizar.tsx:84-105`

## Explicação para leigos
Os modais de autorização marcam o login com `autoFocus`, mas o componente compartilhado do modal manda o foco para o botão “Fechar” quando abre. O usuário pode começar a digitar e o campo deixar de ser o foco ativo.

## Evidência e análise técnica
Os dois modais de autorização passam `autoFocus` ao `Input` de login. O componente `Modal` executa, no efeito de abertura, `closeRef.current?.focus()`. Esse efeito ocorre depois da montagem dos filhos e contradiz o foco inicial definido pelo formulário. O componente ainda não possui uma propriedade de foco inicial nem uma restauração coordenada para o primeiro controle útil.

## Impacto
A operação sem mouse fica imprevisível, especialmente no fluxo de desconto da pré-venda. O operador pode digitar no controle errado, perder tempo e até acionar uma ação por teclado involuntariamente.

## Solução proposta
Implementar foco inicial configurável no modal, priorizando o primeiro controle habilitado quando nenhum alvo for informado. Preservar o foco anterior somente ao fechar, ignorar mudanças internas de estado e adicionar teste de acessibilidade que abre o modal e verifica `document.activeElement`.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ ui.tsx
-  closeRef.current?.focus();
+  const initial = dialogRef.current?.querySelector<HTMLElement>(
+    '[data-autofocus], input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
+  );
+  (initial ?? closeRef.current)?.focus();
```

