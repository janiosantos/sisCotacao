# Índice de capturas do ERP

> **Ambiente:** DEV local · **Data:** 02/09/2026 · **Perfil usado:** administrador de demonstração

As imagens abaixo foram capturadas navegando pelo sistema real. As capturas de
clientes, fornecedores, usuários, pedidos e financeiro foram anonimizadas no
DOM antes de serem gravadas; nenhum dado foi alterado no banco. Capturas de
ação abrem formulários, abas ou modais sem confirmar operações destrutivas.

## Cobertura por módulo

| Frente | Tela principal | Ações e subtelas capturadas |
|---|---|---|
| Operação | [Painel](dashboard-desktop-dev.png), [Pré-venda](pre-venda-desktop-dev.png), [Orçamentos](orcamentos-desktop-dev.png), [Caixa](caixa-desktop-dev.png), [Pós-venda](posvenda-desktop-dev.png) | [Cliente no PDV](pre-venda-cliente-desktop-dev.png), [Detalhe do orçamento](orcamentos-detalhes-desktop-dev.png), [Nova interação](posvenda-nova-interacao-desktop-dev.png), [Garantia](posvenda-garantia-desktop-dev.png), [Devolução/troca](posvenda-devolucao-desktop-dev.png) |
| Cadastros | [Catálogo](catalogo-desktop-dev.png), [Produtos](produtos-desktop-dev.png), [Clientes](clientes-desktop-dev.png), [Parceiros](parceiros-desktop-dev.png), [Vendedores](vendedores-desktop-dev.png), [Categorias](categorias-desktop-dev.png), [Unidades](unidades-desktop-dev.png) | [Novo produto](produtos-novo-desktop-dev.png), [Etiquetas](produtos-etiquetas-desktop-dev.png), [Importar lote](produtos-importar-lote-desktop-dev.png), [Famílias](produtos-familias-desktop-dev.png), [Novo cliente](clientes-novo-desktop-dev.png), [Crediário](clientes-crediario-desktop-dev.png), [Editar cliente](clientes-editar-desktop-dev.png), [Novo parceiro](parceiros-novo-desktop-dev.png), [Novo vendedor](vendedores-novo-desktop-dev.png) |
| Compras | [Compras](compras-desktop-dev.png), [Fornecedores](fornecedores-desktop-dev.png), [Histórico de preços](historico-desktop-dev.png), [Cotações legadas](cotacoes-desktop-dev.png), [Solicitações legadas](solicitacoes-desktop-dev.png) | [Sugestões de compra](compras-sugestoes-desktop-dev.png), [Nova cotação](compras-nova-cotacao-desktop-dev.png), [Cotações](compras-cotacoes-desktop-dev.png), [Pedidos de compra](compras-pedidos-desktop-dev.png), [Novo fornecedor](fornecedores-novo-desktop-dev.png), [Editar fornecedor](fornecedores-editar-desktop-dev.png) |
| Estoque | [Estoque](estoque-desktop-dev.png), [Qualidade do catálogo](diagnostico-variacoes-desktop-dev.png) | [Curva ABC](estoque-abc-desktop-dev.png), [Inventário](estoque-inventario-desktop-dev.png), [Endereços](estoque-enderecos-desktop-dev.png) |
| Financeiro | [Financeiro](financeiro-desktop-dev.png), [Bancos](bancos-desktop-dev.png), [Plano de contas](plano-contas-desktop-dev.png) | [Entrada](financeiro-entrada-desktop-dev.png), [Saída](financeiro-saida-desktop-dev.png), [Receber](financeiro-receber-desktop-dev.png), [Condições](financeiro-condicoes-desktop-dev.png), [Nova conta bancária](bancos-nova-conta-desktop-dev.png) |
| Comercial | [Preços](precos-desktop-dev.png) | [Nova tabela](precos-nova-tabela-desktop-dev.png), [Simulador](precos-simulador-desktop-dev.png) |
| Fiscal | [Fiscal](fiscal-desktop-dev.png) | [Simulador fiscal](fiscal-simulador-desktop-dev.png), [Histórico fiscal](fiscal-historico-desktop-dev.png) |
| Administração | [Usuários](usuarios-desktop-dev.png), [Perfis](perfis-desktop-dev.png), [Configurações](configuracoes-desktop-dev.png), [Atualizações](atualizacoes-desktop-dev.png), [Webhooks](webhooks-desktop-dev.png) | As abas internas de configurações, atualizações e webhooks estão representadas nas capturas principais; ações de alteração não foram confirmadas. |

## Estados complementares

- [Central de ajuda desktop](manual-central-dev.png) e [mobile](manual-central-mobile-dev.png).
- [PDV sem cliente selecionado](pre-venda-dados-desktop-dev.png) e [Caixa sem pedido selecionado](caixa-acoes-desktop-dev.png) documentam ações corretamente desabilitadas por falta de contexto.
- As capturas devem ser regeneradas sempre que houver mudança estrutural de tela, fluxo, contrato visual, permissão ou atalho.
- A captura de [Relatórios](relatorios-desktop-dev.png) registra um bloqueio observado no DEV: “Sem acesso” para o administrador. Isso é pendência de RBAC/funcionalidade, não deve ser tratado apenas com mudança visual.
