# Compras e fornecedores

## Compras (`#/compras`)

**O que é?** Pipeline **Solicitação → Cotação → Análise → Pedido → Recebimento**.
**Para que serve?** Comprar melhor, comparar unidade/preço/prazo e gerar entrada
correta. **Papel:** conecta demanda, fornecedor, estoque e contas a pagar.

1. Adicione itens ou use uma necessidade de reposição.
2. Convide fornecedores e acompanhe respostas.
3. Compare preço líquido, embalagem, fator, marca, prazo e disponibilidade.
4. Gere pedido somente com proposta utilizável.
5. Receba conferindo depósito, documento, quantidades e divergências.

Não confirme o mesmo pedido duas vezes. Recebimento parcial deve manter o saldo
pendente, gerar parcelas corretas e impedir duplicidade.

## Fornecedores (`#/fornecedores`)

**O que é?** Cadastro da contraparte da compra. **Para que serve?** Manter CNPJ,
contatos, categoria, prazo, avaliação e condição. **Papel:** alimenta convites,
pedidos, recebimento e contas a pagar.

Pesquise antes de cadastrar, valide documento, mantenha contatos atualizados e
inative quem não deve receber novos convites.

## Solicitações legadas (`#/solicitacoes`) e Cotações legadas (`#/cotacoes`)

Continuam acessíveis por compatibilidade, mas o fluxo preferencial é **Compras**.
Use o detalhe para transformar necessidade em cotação e não duplique documentos.

## Histórico (`#/historico`)

Consulte preços anteriores por produto/fornecedor comparando sempre unidades
equivalentes e condições comerciais.

## Auditoria

Convite, resposta, escolha, pedido, recebimento, estoque, contas a pagar e
divergência devem formar uma cadeia consultável.
