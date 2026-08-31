# Catálogo de estados e transições — ERP Casa LM

> **GOV-003 do plano mestre.** Centraliza as máquinas de estado de pedido de venda,
> compra, recebimento, estoque, fiscal, financeiro, devolução e garantia. Cada
> transição tem `from`, `to`, comando, permissão, pré-condições, efeitos, evento,
> idempotência e estorno. **Proibido** `PATCH` livre de status em documentos críticos.

## Legenda por linha

`de → para | comando | permissão | pré-condição | efeitos | idempotência | estorno`

## 1. Pedido de venda (orçamento→pedido)

- `rascunho → ativo` | salvar | `orcamentos.editar` | existe itens | — | idempotente | — 
- `ativo → rascunho` | voltar | `orcamentos.editar` | sem vínculo | — | — | —
- `rascunho/ativo → em_analise` | submeter | `orcamentos.cadastrar` | — | — | — | —
- `em_analise → liberado` | aprovar | `orcamentos.aprovar` | — | — | — | —
- `liberado → finalizado` | **converter (pedido)** | `orcamentos.aprovar`/`autoriza_desconto` | alçada+estoque+fiscal ok | EST baixa, FIN conta a receber | chave conversão | `reabrir` (com alçada, sem boleto)
- `finalizado → recebido` | caixa | `financeiro.receber` | — | FIN recebimento, FIS NFC-e | idempotente webhook | estorno no caixa
- `finalizado → liberado` | **reabrir** | `orcamentos.aprovar`/`autoriza_desconto` | sem boleto emitido | estorna contas a receber | — | —
- `qualquer → cancelado` | cancelar | `orcamentos.excluir` | — | estorna reserva/estoque/financeiro | — | reverter via novo doc
- `finalizado → devolvido` | devolução | `posvenda.*` | RMA aprovado | EST entrada, FIN estorno, FIS evento | — | —

Fonte de verdade atual: `catalog_server/orcamento_status.py` (transições controladas).

## 2. Compra (pedido de compra)

- `rascunho → aprovado` | aprovar | `compras.aprovar` (COM-010) | alçada ok | — | — | —
- `aprovado → enviado` | enviar | `compras.enviar` | fornecedor + itens | outbox e-mail/WhatsApp | chave envio | —
- `enviado → confirmado` | confirmação | `compras.*` | resposta fornecedor | — | idempotente | —
- `enviado/confirmado → parcialmente_recebido` | receber parcial | `compras.receber` (REC) | não excede saldo | EST entrada, FIN contas a pagar | chave recebimento | estorno do recebimento
- `parcialmente_recebido → recebido` | receber | idem | saldo zerado | — | idem | —
- `qualquer → cancelado` | cancelar | `compras.*` | saldo não recebido | — | — | —
- `aprovado → enviado` mantém versão; conteúdo congelado após envio (alteração = nova versão autorizada).

Fonte de verdade atual: `compras` (pedidos_compra, cotacoes) — transições a formalizar no service.

## 3. Recebimento (REC-001..003)

- `aguardando_conferência → divergente` | conferir | `estoque.*`/`compras.receber` | divergência detectada | — | — | —
- `divergente → aprovado` | aprovar divergência | `compras.aprovar` | tolerância/documentação | postagem definitiva | — | —
- `divergente → rejeitado` | rejeitar | `compras.*` | motivo | recusa de itens | — | —
- `aprovado → postado` | postar | `compras.receber` | transação única | EST entrada, FIN título, FIS snapshot, CONT | chave postagem | estorno completo
- Dois recebimentos do mesmo pedido são permitidos sem ultrapassar saldo; retry não duplica.

## 4. Estoque (fatos — EST-002)

- Movimentos são **imutáveis**; não existe edição de movimento.
- Correção: **estorno** (`tipo=estorno`, referencia o fato original) + novo fato.
- Saldo é **derivado** do ledger; reconciliação (ARC-005) identifica divergência.

## 5. Fiscal (FIS-002/004/005)

- `pendente → autorizado | rejeitado | denegado` | transmitir | `fiscal.emitir` | cert/vigência | FIS evento | chave por ref. | cancelamento/inutilização
- Contingência NFC-e (FIS-004): habilitação por flag/permissão; série/numeração própria; transmissão posterior preserva vínculo/ordem.
- Não liberar produção sem artefatos externos + aprovação (FIS-001..006).

## 6. Financeiro (títulos)

- `aberto → pago` | receber/pagar | `financeiro.receber`/`.pagar` | forma validada | caixa + baixa | idempotente (webhook/consulta) | estorno
- `aberto → cancelado` | cancelar | `financeiro.*` | — | — | — | —
- Parcelas compartilham `grupo_id`; estorno de parcela preserva pagas.

## 7. Devolução do cliente / RMA (POS-001/002)

- `solicitada → autorizada` | autorizar | `posvenda.*` | política/validação | — | — | —
- `autorizada → recebida` | receber | `estoque.*` | item/lote | EST entrada | — | —
- `recebida → analisada` | analisar | `posvenda.*` | laudo | — | — | —
- `analisada → concluída | rejeitada` | concluir/rejeitar | `posvenda.*` | — | FIN estorno/crédito, FIS evento | chave | —
- Devolução acima do vendido é bloqueada; efeitos sempre com origem.

## 8. Garantia (POS-003)

- `ativa → acionada → cancelada → vencida` (transições existentes em `posvenda`).
- Com fornecedor: laudo, anexos, nº série, custos, responsabilidade, SLA (a completar).
- Retorno ao estoque/quarentena rastreado.

## Regras de implementação

1. Toda transição gera **auditoria** (ator Bearer, ação, alvo, antes/depois mascarado, motivo, IP, correlation_id).
2. Transição inválida retorna **erro estável** (`{error, code}`) e nunca silencioso.
3. Comando que altera mais de uma entidade roda em **transação única + lock + idempotência**.
4. `PATCH` de status em documento crítico deve ser **substituído** pelo comando correspondente (ex.: `POST .../reabrir`, `.../receber`), seguindo o padrão já adotado no lifecycle de orçamento→pedido.