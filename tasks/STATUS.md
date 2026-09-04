# Auditoria — Verificação e Correções

Data: 2026-09-03. Cada achado foi **verificado** contra o código antes de corrigir
(nenhum foi tratado como verdade absoluta). Status final de cada relatório:

## Rodada 1 (001–013)

| # | Relatório | Verificação | Correção |
|---|---|---|---|
| 001 | Páginas sensíveis/impressão sem autorização | ✅ confirmado (5 rotas de impressão sem auth; `/images` público) | ✅ `_autorizar_impressao()` (sessão + `impressao.imprimir`) nas 5 rotas; `/images/comprovantes|anexos` bloqueado |
| 002 | Staging sem segredo + webhook sem assinatura | ✅ confirmado (fallback `catalog-server-local-dev`; webhook aceita sem segredo fora de produção) | ✅ `config.py` exige segredo em staging; `payments/base.py` exige assinatura em staging; compose+workflow de staging com `CATALOG_ENV=staging` e segredos obrigatórios |
| 003 | Anexo financeiro sem whitelist | ✅ confirmado (extensão bruta, sem magic bytes) | ✅ whitelist PDF/PNG/JPG + magic bytes (mesma política do comprovante) + download autenticado (`/api/financeiro/anexo/.../download`, `/api/financeiro/receber/.../comprovante/download`) |
| 004 | Emissão fiscal não-produção (gerador) | ✅ confirmado (nfe_gerador ativo no endpoint; chave `aamm="0000"`, concorrência no número) | ⏸️ **Fiscal — FISCAL_REVIEW_REQUIRED**: mudanças profundas no gerador exigem o módulo tributário; a emissão real está no caminho FISCAL_ENGINE_V2/Focus (homologação pendente). Documentado, não alterado. |
| 005 | `last_insert_rowid()` incompatível com PG | ✅ confirmado (`fiscal_avancado.py:38`) | ✅ `INSERT ... RETURNING id` |
| 006 | RBAC `/api/nfe/emitir/<id>` mapeado p/ `cadastrar` | ✅ confirmado (gate exige `fiscal.cadastrar` antes do decorator `fiscal.emitir`) | ✅ `_acao_da_rota` retorna `emitir` para `POST /api/nfe/emitir/` |
| 007 | Relatório vendas duplica CMV | ✅ confirmado (2 linhas do mesmo produto + custo agregado por (orcamento,produto) → soma 2×) | ✅ `linhas` consolidada por pedido/produto (MIN nos rótulos; GROUP BY sem nome/sku) |
| 008 | Relatório compras filtra data diferente do exibido | ✅ parcial (analítico já usava COALESCE 3 campos; sintético usava 2) | ✅ sintético alinhado ao COALESCE de 3 campos (`data_pedido/data_geracao/criado_em::date`) |
| 009 | Listagens sem paginação | ✅ confirmado (clientes/fornecedores sem limit/offset) | ✅ endpoints novos `pagina` (clientes + fornecedores) com busca server-side; contrato antigo preservado |
| 010 | Modal rouba foco do campo | ✅ confirmado (`closeRef.focus()` após autoFocus do filho) | ✅ foco inicial no primeiro controle útil (input/select/textarea) com fallback no botão Fechar |
| 011 | Tabelas fora do padrão ERP | ✅ confirmado (grades próprias fora do contrato `Table`) | ⏸️ **Dedicado UX**: migração p/ primitives grid no PDV/compras/cotações/perfis é refatoração ampla que pode quebrar o contrato de teclado do PDV — documentado para sessão própria |
| 012 | OpenAPI incompleto | ✅ confirmado (cobertura 138/442 rotas) | ✅ criado `scripts/check_openapi_coverage.py` (mede cobertura; `--strict` bloqueia). Documentação completa das 442 rotas é esforço dedicado (fase 2). |
| 013 | Estoque venda/devolução legado sem rastreabilidade | ✅ confirmado (venda usa `movimentar()` no ramo não-bloqueado; devolução engole exceções) | ✅ **crítico corrigido**: venda sempre via `movimentar_fato` (origem venda + idempotência + custo; `permitir_saldo_negativo` preserva a config de bloqueio como validação); devolução em transação única com fato idempotente (`origem_tipo=devolucao`), sem `except: pass` — rollback e erro se falhar |

**Fixes que também acompanham**: `cancelar_por_documento` aceita `_conn` (transação da devolução).

## Rodada 2 (014–025)

| # | Relatório | Verificação | Correção |
|---|---|---|---|
| 014 | OpenAPI check falsos negativos (HEAD/OPTIONS) | ✅ confirmado (filtro exclui rotas com OPTIONS, quase todas) | ✅ comparação por pares `(path, method)` excluindo HEAD/OPTIONS; `spec_paths` removido |
| 015 | OpenAPI check altera estado (migrações/workers) | ✅ confirmado (`create_app()` roda migrações + `start_worker`) | ✅ `create_app(bootstrap=False, start_workers=False)` no verificador |
| 016 | Saldo negativo diverge do ledger (`max(0,...)`) | ✅ confirmado (`estoque.py:303,314` usa `max(0, saldo - q)`) | ✅ removido `max(0,...)` — saldo persistido como ledger (negativo quando política permite) |
| 017 | Staging cria admin com senha aleatória desconhecida | ✅ confirmado (bootstrap roda em staging com `token_urlsafe`) | ✅ bootstrap restrito a `development/test` + `ALLOW_BOOTSTRAP_ADMIN=1` |
| 018 | Sessão de usuário inativo mantém impressão | ✅ confirmado (`_carregar` não valida `ativo` antes de compor permissões) | ✅ `_carregar` retorna `{}` para inativos; `_autorizar_impressao` valida `usuario_repo.esta_ativo()` |
| 019 | Lead time com denominador inconsistente | ✅ confirmado (numerador usa `data_pedido`; filtro usa COALESCE 3 campos) | ✅ numerador/filtro/denominador usam `COALESCE(data_pedido::date, data_geracao::date, criado_em::date)` |
| 020 | Flask dev server em produção | ✅ confirmado (`CMD python -m catalog_server.run_server`) | ✅ `gunicorn --preload` com 3 workers/4 threads/60s timeout; `run_server:app` importável |
| 021 | PostgreSQL sem pool de conexões | ✅ confirmado (`PgConnection` descarta engine no `close()`) | ✅ engine cache por URL com `QueuePool` (size=10, overflow=20, recycle=1800s) |
| 022 | Credencial de host versionada (senha SSH) | ✅ confirmado (`AGENTS.md:229,234` expõe senha `Mudar@123`) | ✅ senha redagada; instrução substituída por "procedimento seguro fora do repositório" |
| 023 | Contabilização falha silenciosa (`except: pass`) | ✅ confirmado (3 locais: compras, estoque ajuste, estoque fato) | ✅ `logging.warning` com `exc_info=True` em vez de `pass` |
| 024 | Dependências backend fora do lock | ✅ confirmado (Dockerfile usa `pip install` sem versões) | ✅ `uv sync --frozen --no-dev`; `uv.lock` copiado; `gunicorn` adicionado ao `pyproject.toml` |
| 025 | Paginação inválida retorna erro interno (500) | ✅ confirmado (`int(request.args.get(...))` sem try/except) | ✅ `try/except (ValueError, TypeError)` → 400 `paginacao_invalida` |

**Não alterado (documentado)**: 004 (fiscal), 011 (tabelas — sessão UX), 012 (completo — esforço fase 2).