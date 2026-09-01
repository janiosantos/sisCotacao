# Contrato de teclado — Pré-venda / PDV (VEN-002)

Documento de referência para os fluxos de teclado do PDV. **Não quebrar** estes
fluxos em nenhuma alteração de UX.

## Regras gerais

- Nenhum componente pode **roubar foco** da linha de busca (busca com debounce
  não move o cursor).
- Tabelas/lista operam **sem mouse** (setas, Enter, Escape).
- Modal de autorização (desconto/alçada) **preserva o login** do operador e
  retorna o foco para a linha original ao fechar.

## Sequência principal (balcão)

1. **Busca**: digitar termo/EAN/SKU + `Enter` adiciona o item (busca rápida
   rankeada — `GET /api/produtos/busca-rapida`).
   - Descrição **vazia + Enter** → avança para a próxima etapa (desconto).
2. **Desconto**: `Enter` confirma o desconto e segue.
3. **Condição de pagamento**: `Enter` seleciona e segue.
4. **Observação**: opcional; `Enter` avança.
5. **Finalizar**: `Enter` conclui o pedido (reserva/estoque/fiscal/financeiro).

## Atalhos

- `F2` — foco na busca.
- `F8` — concluir venda.
- `Escape` — cancelar modal/ação corrente (sem perder o pedido).
- `Tab`/`Shift+Tab` — navegar campos do formulário corrente (foco visível).

## Feedback

- Produto **indisponível** explica saldo/reserva na própria linha
  (`disponibilidade` da busca rápida).
- Estado `loading`, `error` e `empty` sempre presentes.