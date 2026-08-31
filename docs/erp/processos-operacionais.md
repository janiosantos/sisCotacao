# Processos operacionais — ERP Casa LM

> **GOV-001 do plano mestre.** Matriz dos processos reais da loja: venda balcão,
> orçamento de obra, reserva, retirada, entrega, compra para reposição, compra
> para cliente, recebimento, devolução, garantia, caixa e fechamento.
> Nenhum agente deve inferir regra ausente — o que não estiver documentado aqui
> é decisão de negócio (registrar `DECISAO-*`).

## Convenções

- **Estados**: os códigos abaixo refletem os fluxos já implementados; o catálogo
  completo com transições está em `contracts/maquinas-estado.md`.
- **Efeitos**: `EST` = estoque, `FIN` = financeiro, `FIS` = fiscal, `CONT` = contábil.
- **Permissão**: recurso/ação RBAC (ver `AGENTS.md` §11). Superuser passa tudo.
- **Responsável pelo aceite**: quem valida o critério do processo.

## Matriz de processos

| Processo | Ator | Documento origem | Estados | Efeitos | Permissão | Exceções | Responsável aceite |
|---|---|---|---|---|---|---|---|
| **Venda balcão** (à vista) | Caixa/Operador | PDV → orçamento `rascunho` | `rascunho→liberado→finalizado→recebido` | EST: baixa ao finalizar; FIN: conta a receber + caixa ao receber; FIS: NFC-e ao receber | `orcamentos.cadastrar`, `financeiro.receber` (caixa) | Cliente padrão CONSUMIDOR id 1 não gera parcela/limite; desconto > alçada exige aprovação | Usuário |
| **Orçamento de obra** | Vendedor | Pré-venda com cliente identificado | `rascunho/ativo/em_analise/liberado` (editável) → `finalizado` (congelado) | EST: baixa ao converter; FIN: parcelas por condição | `orcamentos.*`, alçada de desconto (`autoriza_desconto`/`orcamentos.aprovar`) | Cliente padrão não aplica limite/parcelamento | Usuário |
| **Reserva / retirada** | Vendedor/Estoquista | Pedido `finalizado` (não recebido) | reservado (conceito EST-001 a implementar) | EST: reserva reduz disponível, não físico | `orcamentos.*`, `estoque.*` | Fluxo formal de reserva ainda não implementado — decidir (DECISAO) | Usuário |
| **Entrega** | Operador/Transporte | Pedido + expedição | entrega parcial/rastreio (INT-005 a implementar) | EST: saída na expedição; FIS: documento por operação | `orcamentos.*`, `expedicao.*` (novo) | Sem módulo de expedição hoje | Usuário |
| **Compra p/ reposição** | Comprador | Necessidade (motor COM-004) → solicitação → cotação → pedido | solicitação `rascunho→enviada→aprovada→cotando→convertida→cancelada`; pedido `rascunho→aprovado→enviado→confirmado→parcial→recebido→cancelado` | FIN: contas a pagar no recebimento; EST: entrada no recebimento | `compras.*`, `solicitacoes.*` | Aprovação por alçada (COM-010) a implementar | Usuário |
| **Compra p/ cliente** | Vendedor/Comprador | Venda + solicitação especial | idem compra + vínculo `origem_tipo='venda'` | FIN/EST idem; FIS: entrada fiscal por operação | `compras.*`, `orcamentos.*` | Compra sob encomenda não vira estoque automático (COM-004) | Usuário |
| **Recebimento** | Estoquista/Comprador | Pedido + NF/XML | `aguardando_conferência→divergente→aprovado→rejeitado` (REC) | EST: entrada; FIN: contas a pagar; FIS: entrada fiscal; CONT: lançamento | `estoque.*`, `compras.receber`, `fiscal.*` | Dois recebimentos do mesmo pedido permitidos sem ultrapassar saldo (REC-001) | Usuário |
| **Devolução ao fornecedor** | Comprador/Estoquista | Recebimento + NF | vinculada ao recebimento/lote | EST: saída; FIN: crédito/estorno a pagar; FIS: evento de saída | `compras.*`, `estoque.*`, `fiscal.*` | Não devolve mais que o recebido (REC-006) | Usuário |
| **Devolução do cliente / troca** | Vendedor/Caixa | Venda (RMA POS-001/002) | `solicitada→autorizada→recebida→analisada→concluída/rejeitada` | EST: entrada; FIN: estorno/novo título; FIS: evento quando aplicável | `posvenda.*`, `orcamentos.*`, `financeiro.*` | Devolução acima do vendido bloqueada; política de troca = DECISAO | Usuário |
| **Garantia** | Vendedor/Estoquista | Venda + laudo | garantia com fornecedor/SLA (POS-003) | EST: retorno/quarentena rastreado; FIS: se envolver NF | `posvenda.*` | Decidir política e SLA (DECISAO) | Usuário |
| **Caixa (abertura→fechamento)** | Caixa | Sessão de caixa | aberto → fechado (VEN-004) | FIN: saldo esperado × contado, diferença justificada | `financeiro.*` | Dois operadores não usam sessão indevida | Usuário |
| **Fechamento de período** | Contador/Admin | Período contábil | fechado (BI-006/EST-003) | bloqueia alteração de movimentos do período | `configurar`/contábil | Período fechado não muda | Contador |

## Documentos de origem por domínio

- **Vendas**: `orcamentos` (orçamento/pedido), `documentos_fiscais` (NFC-e/NF-e), `contas_receber`.
- **Compras**: `solicitacoes_compra`, `cotacoes`, `cotacao_itens/precos`, `pedidos_compra`.
- **Estoque**: `estoque_movimentos`, `estoque_saldo` (derivado), `lotes` (quando implementado), inventário (EST-006).
- **Financeiro**: `contas_pagar`, `contas_receber`, `caixa` (movimentos), `contabil_lancamentos`, `plano_contas`.
- **Fiscal**: `documentos_fiscais`, `fiscal_snapshot`, entrada XML (REC-004/FIS-006).

## Regra geral de efeitos

Qualquer operação que altera mais de uma entidade de negócio roda em **transação única**
com locks e idempotência (`AGENTS.md`). Corrigir nunca é UPDATE direto em fato: usa-se
**estorno + novo fato**. Saldo de estoque é derivado/reconciliável, não editado.