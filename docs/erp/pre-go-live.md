# Preparacao da producao para o go-live

## Objetivo

Remover a massa de testes da instancia de producao antes da entrada real em
operacao, preservando configuracoes administrativas e todas as imagens do
catalogo anterior em uma galeria independente.

Esta rotina e excepcional. Depois do go-live, produtos e fatos de estoque,
compra, venda, financeiro e fiscal nunca devem ser apagados dessa forma.

## O que permanece

- Usuarios, perfis, permissoes e auditoria de RBAC.
- Configuracao da loja, emitente, provedores de pagamento e integracoes.
- Plano de contas, centros de custo, condicoes de pagamento e gatilhos contabeis.
- Regras e tabelas fiscais, IBPT, NCM, CEST, CFOP, CST e CSOSN.
- Grupos, subgrupos, categorias, subcategorias, familias, atributos, marcas e unidades.
- Depositos e posicoes fisicas, politicas comerciais e configuracoes de precificacao.
- Historico de releases/migrations e configuracao da impressora.
- Usuarios/RBAC e politica generica do programa de parceiros.

Os usuarios preservados sao listados no inventario para revisao. O `dry-run`
recusa a execucao enquanto o usuario `admin` usar a senha de teste conhecida.
Regras de alcada vinculadas a fornecedores de teste sao removidas; regras
genericas permanecem.

## O que e removido

- Produtos e todos os vinculos por produto, inclusive precos, identificadores,
  perfis fiscais, conversoes, imagens e relacionamentos.
- Clientes, fornecedores, transportadoras e profissionais parceiros de teste,
  incluindo contatos, crediario, indicacoes, pontos e bonificacoes.
- Vendedores e contas bancarias cadastrados durante os testes; os registros
  reais devem ser criados depois da limpeza.
- Orcamentos, pedidos, pagamentos, caixa, expedicao, pos-venda, comissoes e fiscal de saida.
- Solicitacoes, cotacoes, pedidos de compra, recebimentos, devolucoes e fiscal de entrada.
- Saldos, movimentos, lotes, enderecamento por produto, inventarios, ABC/XYZ e demanda.
- Contas a pagar/receber, anexos, comprovantes, extratos, movimentos bancarios e
  lancamentos contabeis produzidos pelos testes.
- Filas, webhooks, outbox, idempotencia, importacoes e logs operacionais de teste.

Depois da limpeza, a rotina recria somente o cliente tecnico `CONSUMIDOR` com
`id=1`, saldo e limite de credito zero.

As filas de teste do Redis sao esvaziadas somente depois do reset confirmado.
Todos os tokens dos usuarios preservados sao revogados, obrigando um novo login.

## Preservacao das imagens

O exportador varre todos os arquivos fisicos de `images/cadastro`, inclusive os
que nao possuem linha em `imagens_produto`. O nome gerado segue:

```text
CAT_SUB_nome-base_marca__P000000_I000000.ext
```

`CAT` e `SUB` sao os tres primeiros caracteres normalizados da categoria e
subcategoria. Os IDs tecnicos no final evitam colisoes entre nomes iguais.

A galeria e instalada em `/home/jpsantos/galeria-produtos`, fora do checkout do
SISCOM. Quando origem e destino estao no mesmo filesystem, sao usados hardlinks:
a renomeacao nao duplica os aproximadamente 16 GiB e apagar o caminho antigo
nao apaga o arquivo preservado. Cada arquivo possui SHA-256 no SQLite.
O exportador verifica previamente o filesystem e o espaco livre; se hardlinks
nao forem possiveis, exige espaco para uma copia integral antes de iniciar.

## Sequencia obrigatoria

1. `inventory`: inventario somente leitura e deteccao de tabelas nao classificadas.
2. Trocar a senha conhecida `admin/admin123` e revisar a lista de usuarios preservados.
3. `export-images`: exportacao integral para a galeria.
4. `deduplicate-images`: quando o Docker nao cria hardlinks entre bind mounts,
   substitui as copias usando uma unica montagem do filesystem do host.
5. `verify-images`: releitura e validacao de todos os checksums.
6. `install-gallery`: instalacao da aplicacao standalone e health check.
7. `dry-run-reset`: relatorio final e token vinculado ao snapshot.
8. Confirmacao explicita do responsavel com o token apresentado.
9. `execute-reset`: para escritores, repete a verificacao integral, valida o
   espaco, gera dump final, reseta em transacao, limpa as filas e valida.
10. `docker-prune`: remove imagens sem container e cache; nunca remove volumes.

O reset usa `TRUNCATE ... RESTRICT`, sem `CASCADE`. Qualquer dependencia nova ou
tabela publica sem classificacao interrompe a execucao antes de apagar dados.

## Rollback de dados

Embora nao haja rollback planejado da aplicacao, o workflow gera um dump final
em `/home/jpsantos/siscom/backups/pre-go-live-*.dump` e seu SHA-256 antes do
reset. Esse backup nao e removido pelo `docker-prune`.
