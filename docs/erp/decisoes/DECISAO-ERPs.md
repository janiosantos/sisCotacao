# Decisões que exigem usuário ou responsável externo (DECISAO-*)

> **GOV-005 / §20 do plano mestre.** Cada decisão documenta opções, impacto/bloqueio e a
> decisão tomada. Todas as 12 foram **fechadas em 2026-08-31** (aprovação do usuário,
> salvo indicação; DECISAO-003 com diretriz específica do usuário). Onde a decisão depende
> de validação formal externa (contador), ela está marcada como **aplicável desde já, com
> confirmação formal a ser anexada na homologação (PIL-003)**.

## Registro de decisões (2026-08-31)

| # | Decisão | Escolha adotada | Status |
|---|---|---|---|
| 001 | Escopo de empresa | **Monoempresa**; modelo preparado para multifilial (`empresa_id`/`filial_id` opcionais) sem simular isolamento | ✅ Decidida |
| 002 | Método de custo | **Custo médio ponderado por depósito**, custo do movimento persistido (frete/descontos/impostos conforme regra) | ✅ Decidida (contador: confirmar na homologação) |
| 003 | Regime/API/certificado | **Simples Nacional** (sistema preparado para **Lucro Real**); API **FOCUS**; **Certificado A1** | ✅ Decidida (diretriz do usuário) |
| 004 | Adquirente/TEF | **Manual no piloto**; adapter depois | ✅ Decidida |
| 005 | Política troca/devolução/garantia | **30 dias** p/ troca com item em condições; garantia conforme fornecedor | ✅ Decidida |
| 006 | Comissão | **% sobre venda líquida** congelado no evento; estorno na devolução | ✅ Decidida |
| 007 | Níveis de serviço | Segurança por **ABC** (A alta, C baixa); lead time real medido quando houver amostra | ✅ Decidida |
| 008 | Margem mínima | Reusar o **mecanismo de alçada de desconto** já implementado | ✅ Decidida |
| 009 | Marketplaces/transportadoras | **Manual no piloto**; adapter depois | ✅ Decidida |
| 010 | LGPD | **Mascarar PII** em logs/relatórios; **consentimento** WhatsApp/e-mail | ✅ Decidida |
| 011 | Lote/série/validade | **Parametrizar por família**; FEFO/FIFO; controlados não entram/saem sem rastreio | ✅ Decidida |
| 012 | Bancos/conciliação | **Conciliação manual assistida**; nenhuma baixa automática sem regra | ✅ Decidida |

---

# DECISAO-001 — Escopo de empresa (monoempresa vs multiempresa/multifilial)

- **Bloqueia:** MDM-001 (contexto de empresa/filial), séries fiscais, caixas, depósitos, preços por filial.
- **Decisão (2026-08-31):** **Monoempresa** — manter escopo único; deixar o modelo preparado
  (`empresa_id`/`filial_id` opcionais) **sem simular isolamento**. Reavaliar multifilial só se a operação crescer.
- **Efeito:** MDM-001 fica **desbloqueado** na forma "decisão registrada + modelo preparado".

# DECISAO-002 — Método oficial de custo de estoque

- **Bloqueia:** EST-003 (custo médio/histórico), EST-004 (valorização), BI-006 (DRE/CMV), margem histórica.
- **Decisão (2026-08-31):** **custo médio ponderado por depósito**, custo do movimento persistido;
  composição do custo (frete/descontos/impostos) conforme regra fiscal. Confirmar com o contador na homologação (PIL-003).

# DECISAO-003 — Regime tributário, matriz fiscal e certificado/provedor

- **Bloqueia:** FIS-001..006, REC-004 (entrada fiscal), VEN-006 (fiscal na venda), contingência.
- **Decisão (2026-08-31, diretriz do usuário):** **Simples Nacional** (deixando claro que o
  sistema deve estar preparado para mudança para **Lucro Real**); API **FOCUS** + **Certificado A1**.
- **Efeito:** FIS-001..006 podem avançar na estrutura (regras Simples, adapter FOCUS, cert A1)
  **sem liberar produção** até homologação e matriz fiscal assinada.

# DECISAO-004 — Adquirente/TEF (cartão) ou escopo manual inicial

- **Bloqueia:** VEN-007 (TEF), INT-002 (liquidação/taxas de adquirente).
- **Decisão (2026-08-31):** **escopo manual inicial** (registrar cartão como recebido com código/bandeira, sem terminal); adapter depois.

# DECISAO-005 — Política de troca, devolução, garantia e crédito

- **Bloqueia:** POS-001..005.
- **Decisão (2026-08-31):** **30 dias** para troca com item em condições; garantia conforme fornecedor; crédito vs estorno definido por RMA.

# DECISAO-006 — Comissão de vendedores

- **Bloqueia:** POS-005.
- **Decisão (2026-08-31):** **% sobre venda líquida** congelado no evento; estorno na devolução.

# DECISAO-007 — Níveis de serviço, estoque de segurança e política de compra

- **Bloqueia:** COM-004/005, EST-005.
- **Decisão (2026-08-31):** estoque de segurança por **ABC** (A alta, C baixa); lead time real quando houver amostra mínima (senão baixa confiança).

# DECISAO-008 — Margem mínima e alçada de preço

- **Bloqueia:** MDM-007, VEN-003.
- **Decisão (2026-08-31):** reutilizar o **mecanismo de alçada de desconto** já implementado para a margem mínima.

# DECISAO-009 — Marketplaces e transportadoras

- **Bloqueia:** INT-004/005.
- **Decisão (2026-08-31):** manter **manual no piloto**; adapter depois.

# DECISAO-010 — LGPD: retenção, consentimento e exportação

- **Bloqueia:** ADM-003.
- **Decisão (2026-08-31):** **mascarar PII** em logs/relatórios; **consentimento** para WhatsApp/e-mail; retenção mínima necessária.

# DECISAO-011 — Famílias com controle de lote/série/validade

- **Bloqueia:** EST-008, REC/PDV para itens controlados.
- **Decisão (2026-08-31):** **parametrizar por família**; FEFO/FIFO; itens controlados não entram/saem sem rastreio.

# DECISAO-012 — Bancos e regras de conciliação

- **Bloqueia:** INT-001.
- **Decisão (2026-08-31):** **conciliação manual assistida**; nenhuma baixa automática sem regra explícita.

---

**Fechamento:** todas as decisões registradas em `CONTEXTO_SESSAO.md` (2026-08-31). Tarefas
antes bloqueadas (MDM-001, EST-003/004, FIS-001..006, VEN-007, POS-001..005, COM-004/005,
MDM-007, INT-*, ADM-003, EST-008, EST-005) **desbloqueadas** no `EXECUCAO_PLANO_MESTRE_ERP.md`,
mantendo os gates de homologação (PIL-003) para custo/fiscal/financeiro.