# Vendas: Painel, Catálogo, Pré-venda, Orçamentos e Caixa

## Painel (`#/dashboard`)

**O que é?** Resumo da operação. **Para que serve?** Priorizar alertas e
indicadores. **Papel:** direciona para o módulo que corrige a origem. Consulte o
período e abra o detalhe antes de tomar decisão.

## Catálogo (`#/catalogo`)

**O que é?** Busca visual de produtos. **Para que serve?** Encontrar SKU,
variação, preço e adicionar itens ao carrinho. **Papel:** entrada comercial sem
substituir o cadastro mestre. Pesquise, confira a unidade e monte a cotação.

## Pré-venda / PDV (`#/pre-venda`)

**O que é?** Tela de atendimento e montagem de venda. **Para que serve?**
Registrar cliente, itens, desconto e condição. **Papel:** conecta cliente,
estoque, crédito, caixa, contas e fiscal.

1. Identifique o cliente ou use **Consumidor Padrão** para venda à vista.
2. Pesquise o produto; `2*produto` adiciona duas unidades.
3. Revise preço, desconto, condição e observação.
4. Com descrição vazia, Enter segue **Desconto → Condição → Observação →
   Finalizar**.
5. Finalize. Venda a prazo exige crediário aprovado; o vendedor não recebe.

## Orçamentos (`#/orcamentos`)

**O que é?** Lista do ciclo proposta → pedido. **Para que serve?** Acompanhar
rascunho, aprovação, conversão, boleto e contas. **Papel:** congela o compromisso
comercial e registra alçada, crédito e estoque.

Filtre o status, abra o detalhe, resolva pendências e somente então converta.
Pedido finalizado é congelado; boleto emitido impede reabertura automática.

## Caixa (`#/caixa`)

**O que é?** Sessão física de caixa. **Para que serve?** Abrir, receber, lançar
sangria/suprimento e fechar. **Papel:** liquida vendas à vista; não administra
crediário. Confira forma, valor, troco e pedido antes de confirmar.

## Quem pode usar?

Vendas opera Pré-venda/Orçamentos; Caixa opera recebimento; aprovadores e
Financeiro executam ações de alçada. O RBAC e o estado do documento são gates.

## Auditoria

Cliente, vendedor, desconto, aprovação, pedido, recebimento e estoque devem
permanecer vinculados ao usuário, horário e documento.
