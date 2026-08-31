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

## B. Decisões bloqueantes (`DECISAO-*`) a abrir no início

| Decisão | Bloqueia | Quem aprova |
|---|---|---|
| Monoempresa vs multifilial | MDM-001 | Usuário |
| Método oficial de custo | EST-003/004, BI-006, FIS | Contador |
| Regime tributário + matriz fiscal + certificado/provedor | FIS-001..006, REC-004, VEN-006 | Contador + usuário |
| Adquirente/TEF (ou escopo manual) | VEN-007, INT-002 | Usuário |
| Política de troca/devolução/garantia/crédito/comissão | POS-001..005 | Usuário |
| Níveis de serviço, estoque de segurança, política de compra | COM-004/005, EST-005 | Usuário |
| Margem mínima/alçada de preço | MDM-007, VEN-003 | Usuário |
| Marketplaces/transportadoras | INT-004/005 | Usuário |
| LGPD (retenção/consentimento) | ADM-003 | Usuário |
| Famílias com lote/série/validade | EST-008 | Usuário |
| Bancos e regras de conciliação | INT-001 | Usuário/banco |

Saída: `docs/erp/decisoes/DECISAO-*.md` (opções + recomendação + bloqueio). Registrar em CONTEXTO. Nenhuma tarefa dependente avança até a decisão.

## C. Ondas de execução (ordem §21 do plano mestre)

| # | Onda | Tarefas | Depende | Bloqueado por decisão |
|---|---|---|---|---|
| 0 | Governança | GOV-001..004 + abrir DECISAO-* | — | — |
| 1 | Dados mestres | MDM-001..007 | Onda 0 | MDM-001 (mono/multi); MDM-007 (margem) |
| 2 | Estoque/custo | EST-001..008 | Onda 1 | EST-003 (custo); EST-008 (lote) |
| 3 | ABC/necessidade | COM-001..006 | Onda 2 | COM-004/005 (níveis) |
| 4 | Compras | COM-007..012 | Onda 3 | COM-010 (alçada) |
| 5 | Recebimento | REC-001..006 | Onda 4 | REC-004 (fiscal) |
| 6 | Venda | VEN-001..007 | Onda 2 | VEN-007 (TEF) |
| 7 | Fiscal | FIS-001..006 | EXTERNO | 100% contador/cert/provedor (só FIS-003/006 estruturais em paralelo) |
| 8 | BI | BI-001..007 + catálogo §18 | Ondas 2/4/5/6 | — |
| 9 | Pós-venda | POS-001..005 | Onda 6 | POS (políticas/comissão) |
| 10 | UX/ARC | UX-001..007, ARC-001..007 | contínuo/paralelo | — |
| 11 | INT/ADM | INT-001..006, ADM-001..005 | decisões | INT/ADM |
| 12 | Piloto | PIL-001..004 | todas P0/P1 | — |

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