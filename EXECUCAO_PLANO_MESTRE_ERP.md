# EXECUCAO_PLANO_MESTRE_ERP — Plano de execução

**Base:** `PLANO_MESTRE_IMPLEMENTACAO_ERP.md` (§21 como ordem canônica) + `AGENTS.md` (diretrizes) + `CONTEXTO_SESSAO.md` (estado real: schema 104, 248 testes BE, 34 testes FE).

**Regra-mestra:** `PLANO_EXECUCAO_8_PENDENCIAS.md` permanece pendente/intocado; este plano substitui a referência de execução. Nenhum deploy/migração não-dev sem confirmação explícita.

## A. Protocolo por tarefa (checklist §19 do plano mestre)

1. Ler `AGENTS.md`/`CONTEXTO_SESSAO.md`/domínio; `git status --short`; mapear consumidores do contrato.
2. Migração versionada (`VERSION`, `RISCO`, `NAME`, `MUDANCA`, `guard`, `forward`, `backward`) testada **vazio→head** e **incremental→head**, idempotente.
3. Mudança incompatível → **Expand/Migrate/Contract em releases separadas**; nunca banco+backend+frontend juntos; frontend só via API.
4. Backend é autoridade (RBAC + auditoria + idempotência + lock); regra ausente → `DECISAO-*` e bloqueia somente a parte dependente.
5. Capacidade nova atrás de flag (GOV-004) com fallback compatível (desligar flag não desfaz migração).
6. Gates por tarefa: `py_compile` → `pytest` (248 hoje) → `npm test` (34 hoje) → `typecheck` → `build` → `git diff --check` → OpenAPI + tipos → `CONTEXTO_SESSAO.md` → commit/push.
7. Staging/produção só com autorização explícita (produção segue em v2.32.2).

## B. Decisões bloqueantes (`DECISAO-*`)

> **Todas as 12 decisões foram fechadas em 2026-08-31** (registro em
> `docs/erp/decisoes/DECISAO-ERPs.md`). Resumo:
> **001** monoempresa (modelo preparado) · **002** custo médio por depósito (contador: confirmar na homologação) ·
> **003** Simples Nacional (preparado p/ Lucro Real) + **FOCUS** + **Certificado A1** ·
> **004** TEF manual no piloto · **005** troca 30 dias, garantia por fornecedor ·
> **006** comissão % venda líquida · **007** segurança por ABC · **008** reusar alçada de desconto ·
> **009** marketplaces manual no piloto · **010** LGPD mascarar PII + consentimento ·
> **011** lote/série parametrizado por família · **012** conciliação manual assistida.

Onde houver nova decisão ausente, criar `DECISAO-*` e bloquear somente a parte dependente.

## C. Ondas de execução (ordem §21 do plano mestre)

| # | Onda | Tarefas | Depende | Observação (decisões fechadas 2026-08-31) |
|---|---|---|---|---|
| 0 | Governança | GOV-001..004 + DECISAO-* | — | DECISAO-001..012 decididas |
| 1 | Dados mestres | MDM-001..007 | Onda 0 | MDM-001 monoempresa; MDM-007 usa alçada de desconto |
| 2 | Estoque/custo | EST-001..008 | Onda 1 | EST-003 custo médio; EST-008 lote por família |
| 3 | ABC/necessidade | COM-001..006 | Onda 2 | Segurança por ABC (COM-004/005) |
| 4 | Compras | COM-007..012 | Onda 3 | Alçada de compra conforme perfil |
| 5 | Recebimento | REC-001..006 | Onda 4 | Entrada fiscal FOCUS (Simples) |
| 6 | Venda | VEN-001..007 | Onda 2 | TEF manual no piloto |
| 7 | Fiscal | FIS-001..006 | EXTERNO | Simples Nacional + FOCUS + Cert A1; produção só após homologação |
| 8 | BI | BI-001..007 + catálogo §18 | Ondas 2/4/5/6 | Custo médio p/ DRE/CMV |
| 9 | Pós-venda | POS-001..005 | Onda 6 | Troca 30 dias; comissão % venda líquida |
| 10 | UX/ARC | UX-001..007, ARC-001..007 | contínuo/paralelo | — |
| 11 | INT/ADM | INT-001..006, ADM-001..005 | — | Conciliação manual; LGPD mascarar PII |
| 12 | Piloto | PIL-001..004 | todas P0/P1 | Homologação fiscal/financeira (contador) |

> FIS (7) fica **em paralelo só nas partes não dependentes**; UX/ARC (10) roda **durante** as ondas 1–9. BI (8) não inicia como relatório final antes de 2/4/5/6.

## D. Primeiro lote executável (Onda 0 + primeiros MDM)

1. **GOV-001** `docs/erp/processos-operacionais.md` (matriz processo/ator/estado/efeitos/permissão/responsável).
2. **GOV-002** `docs/erp/contracts/dicionario-dados.md` (convenções `id`/`correlation_id`/erros/paginação).
3. **GOV-003** `docs/erp/contracts/maquinas-estado.md` (8 máquinas; fonte para eliminar `PATCH` livre).
4. **GOV-004** registrar flags `motor_compras`/`abc_historica`/`custo_historico`/`entrada_fiscal`/`novo_recebimento` em `flags.py` + painel.
5. **DECISAO-001..011** abrir decisões (seção B).
6. **MDM-002** `unidade_conversao` (Expand; preserva `unidade_venda`) + cálculo `1 CX=N UN` com unidade base.
7. **MDM-003** `produto_identificador` (EAN múltiplo/código interno/fabricante/fornecedor/embalagem; busca exata antes de textual; bloqueio de duplicidade).
8. **MDM-006** workflow `rascunho→revisão→publicado→bloqueado` + importação com prévia/simulação e commit idempotente.

**Prontidão Onda 0+1:** GOV documentado, flags registradas, DECISAO-* abertas, MDM-002/003/006 com migração + API/OpenAPI + tipos + testes + UI desktop/mobile, CONTEXTO atualizado, sem deploy.

## E. Gate final (PIL-004)

Checklist P0 + evidências operacionais P1 + aprovação explícita de publicação. Produção segue em v2.32.2 até lá.