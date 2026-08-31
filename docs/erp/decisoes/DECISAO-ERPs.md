# Decisões que exigem usuário ou responsável externo (DECISAO-*)

> **GOV-005 / §20 do plano mestre.** Estas decisões **não podem ser inventadas** pelo
> agente. Cada uma documenta opções, impacto/bloqueio e uma recomendação inicial.
> Enquanto estiver `ABERTA`, somente a parte dependente da decisão fica bloqueada;
> o restante do plano segue. Registrar a decisão final no `CONTEXTO_SESSAO.md`.

## DECISAO-001 — Escopo de empresa (monoempresa vs multiempresa/multifilial)

- **Bloqueia:** MDM-001 (contexto de empresa/filial), séries fiscais, caixas, depósitos, preços por filial.
- **Opções:**
  1. **Monoempresa** (recomendado para o piloto): manter escopo único; deixar o modelo preparado (`empresa_id`/`filial_id` opcionais) sem simular isolamento.
  2. Multiempresa/multifilial: criar `empresas`/`filiais`, contexto autenticado, Expand + backfill + dual read/write.
- **Quem aprova:** usuário. **Recomendação inicial:** monoempresa agora, modelo preparado.

## DECISAO-002 — Método oficial de custo de estoque

- **Bloqueia:** EST-003 (custo médio/histórico), EST-004 (valorização), BI-006 (DRE/CMV), margem histórica.
- **Opções:** custo médio ponderado (recomendado para varejo) · PEPS/FIFO · custo específico · UEPS (raro/contraindicado).
- **Quem aprova:** **contador** (composição do custo: frete/descontos/impostos conforme regra fiscal). **Recomendação inicial:** média ponderada por depósito, custo do movimento persistido.

## DECISAO-003 — Regime tributário, matriz fiscal e certificado/provedor

- **Bloqueia:** FIS-001..006, REC-004 (entrada fiscal), VEN-006 (fiscal na venda), contingência.
- **Opções:** Simples Nacional presumido/real (definir CFOP/CST/CSOSN/PIS/COFINS por operação), proveedor Focus/TecnoSpeed, certificado A1/A3.
- **Quem aprova:** **contador + usuário** (credenciais/certificado). `FISCAL_ENGINE_V2` permanece desligada em produção até aqui.

## DECISAO-004 — Adquirente/TEF (cartão) ou escopo manual inicial

- **Bloqueia:** VEN-007 (TEF), INT-002 (liquidação/taxas de adquirente).
- **Opções:** 1) escopo manual inicial (recomendado: registrar cartão como recebido com código/bandeira, sem terminal); 2) integrar adquirente/TEF via adapter.
- **Quem aprova:** usuário. **Recomendação inicial:** manual no piloto, adapter depois.

## DECISAO-005 — Política de troca, devolução, garantia e crédito

- **Bloqueia:** POS-001..005 (prazos, condições, crédito de cliente, garantia/SLA).
- **Opções:** prazos (ex.: 7/30 dias), condição do item, crédito vs estorno, garantia por família/fornecedor.
- **Quem aprova:** usuário (política comercial). **Recomendação inicial:** 30 dias p/ troca com item em condições; garantia conforme fornecedor.

## DECISAO-006 — Comissão de vendedores

- **Bloqueia:** POS-005 (base e percentual por venda/margem/recebimento/devolução).
- **Opções:** % sobre venda líquida, sobre margem, por forma de pagamento, estorno na devolução.
- **Quem aprova:** usuário. **Recomendação inicial:** % sobre venda líquida congelado no evento.

## DECISAO-007 — Níveis de serviço, estoque de segurança e política de compra

- **Bloqueia:** COM-004/005 (motor de reposição, lead time), EST-005 (parâmetros de planejamento).
- **Opções:** metas de cobertura (ex.: dias), estoque de segurança por ABC/XYZ, fornecedor preferencial por grupo.
- **Quem aprova:** usuário. **Recomendação inicial:** segurança por ABC (A alta, C baixa) e lead time medido real quando houver amostra.

## DECISAO-008 — Margem mínima e alçada de preço

- **Bloqueia:** MDM-007 (preço/margem), VEN-003 (desconto).
- **Opções:** margem mínima por grupo/marca; alçada de desconto por perfil (já existe alçada de desconto); aprovação acima da margem.
- **Quem aprova:** usuário. **Recomendação inicial:** reutilizar o mecanismo de alçada de desconto já implementado.

## DECISAO-009 — Marketplaces e transportadoras

- **Bloqueia:** INT-004 (e-commerce/marketplaces), INT-005 (transporte/entrega).
- **Opções:** integrar marketplace(s) específico(s) ou começar manual; transportadora própria vs integração de frete.
- **Quem aprova:** usuário. **Recomendação inicial:** manter manual no piloto; adapter depois.

## DECISAO-010 — LGPD: retenção, consentimento e exportação de dados

- **Bloqueia:** ADM-003 (classificação de campos, mascaramento, retenção, anonimização).
- **Opções:** prazos de retenção de PII/financeiro, consentimento de comunicação, relatório de exportação.
- **Quem aprova:** usuário (jurídico se necessário). **Recomendação inicial:** mascarar PII em logs/relatórios, consentimento de WhatsApp/e-mail.

## DECISAO-011 — Famílias com controle de lote/série/validade

- **Bloqueia:** EST-008 (rastreabilidade), REC/PDV para itens controlados.
- **Opções:** controlar por família (ex.: produtos com validade/norma) vs geral; FEFO/FIFO.
- **Quem aprova:** usuário. **Recomendação inicial:** parametrizar por família; itens controlados não entram/saem sem rastreio.

## DECISAO-012 — Bancos e regras de conciliação

- **Bloqueia:** INT-001 (importação OFX/CSV, matching, conciliação).
- **Opções:** quais bancos, tolerância de matching, regra de baixa automática (só com regra explícita).
- **Quem aprova:** usuário/banco. **Recomendação inicial:** conciliação manual assistida; nenhuma baixa automática sem regra.

---

**Como fechar:** para cada decisão, registrar em `CONTEXTO_SESSAO.md` a opção escolhida,
o responsável e a data; então desbloquear as tarefas dependentes marcadas em `EXECUCAO_PLANO_MESTRE_ERP.md`.