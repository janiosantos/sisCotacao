# TODO — Análise e correção de possíveis bugs (para Codex)

> Este arquivo é um checklist para uma **análise de código focada em bugs**. Leia
> `AGENTS.md` e `CONTEXTO_SESSAO.md` antes de começar. Siga as convenções de
> teste (pytest, typecheck) e **NUNCA faça deploy** — apenas commit/push.

## Instruções gerais
- Contexto: ERP Casa LM (`ecommerce_scraper`), Flask + PostgreSQL 16 + React/Vite.
- Testes: `pytest` (env `TEST_PG_URL=postgresql+psycopg://catalog:catalog@localhost:5432/catalog_test`), 248 verdes hoje.
- Ao corrigir: rodar `py_compile`, os testes do módulo tocado e a suíte completa.
- Registrar o resultado ao final deste arquivo (seção "Resultado da análise").

---

## 1. Armazenamento de imagens — ALTA prioridade (área que já causou perda de dados)

Revisar a cadeia completa após as migrações 0093/0094/0096 (caminhos relativos, remoção de `url_origem`):

- [ ] `backend/catalog_server/services/imagens_service.py`
  - `_save_bytes` retorna **str relativo** (`cadastro/<id>/<nome>`) — confirmar que NENHUM chamador ainda trata como `Path` absoluto.
  - `salvar_uploads`/`baixar_de_url`/`_relpath`/`remover_arquivo` (resolve contra `IMAGES_DIR`) consistentes.
  - `_conteudo_duplicado` lê de `_folder(produto_id)` = `IMAGES_DIR/cadastro/<id>` — correto com caminhos relativos?
- [ ] `backend/catalog_server/services/imagens_lote.py` — `baixar_lote` usa o retorno relativo de `_save_bytes`; contadores `aplicadas`/`deduplicadas` corretos? favorita → capa?
- [ ] `backend/catalog_server/services/parse_url_service.py` e `backend/catalog_server/importar_catalogo.py` — INSERTs sem `url_origem`; nenhuma referência remanescente a `url_origem` em código (grep).
- [ ] `backend/catalog_server/repositories/produtos.py` — `add_imagem` sem `url_origem`; `delete_imagem`/`remover_arquivo` com caminho relativo.
- [ ] Migrações `0093/0094/0096`: idempotência (rodar 2x não corrompe), comportamento em banco vazio→head.
- [ ] **grep global**: `url_origem`, `_save_bytes(`, `str(target)` — nenhuma referência quebrada.

## 2. API pública `/api/publico/*` — ALTA prioridade

- [ ] `backend/catalog_server/blueprints/api_publico.py`
  - Ciclo de vida das conexões (`with system_conn()`) — houve bug de usar `conn` fora do bloco; conferir TODAS as funções.
  - Sanitização completa: nenhum campo interno (custo, NCM, fornecedores, classe_abc) vaza na listagem/detalhe.
  - Paginação: `has_more` correto; `limit` capado em 100.
  - Filtro `grupo` (código/nome, ILIKE) + `/api/publico/grupos` (produto inexistente → 404?).
  - CORS (headers) e preflight OPTIONS.
- [ ] `backend/catalog_server/repositories/catalog.py`
  - `list_products`/`_browse_flat`/`resumo_abc`: adição do parâmetro `grupo` não quebrou ordem de params/WHERE (SQL injection?); `_flat_card` campos `grupo`/`grupo_nome`.
  - Confirmar que outros chamadores de `list_products`/`resumo_abc` (blueprints internos) continuam corretos com a assinatura nova.

## 3. Imagens em lote (fornecedor) — revisar lógica

- [ ] `imagens_lote.py`: `buscar_fornecedor`, `preview_imagens` (dedup MD5, dimensões), `baixar_lote` (retry 1x, limites 20/20, dedup por produto, `deduplicadas`).
- [ ] Tratamento de erros de rede/timeout (requests) e HTML/JS-rendered dos sites (casadoeletricistasc vs casadosparafusos/anhanguera).

## 4. Infraestrutura TLS/nginx — revisar

- [ ] `frontend/nginx-entrypoint.sh`: seleção TLS/HTTP, wait do cert, loop de reload (`stat -c %Y`), traps/signals (shutdown limpo).
- [ ] `frontend/nginx.backend-routes.conf`: proxy com **variável** + `resolver 127.0.0.11` — confirmar que o comportamento do proxy não mudou (URI pass-through, headers). Possível efeito colateral conhecido de `proxy_pass` com variável.
- [ ] `frontend/nginx.conf` / `nginx.http.conf`: `default_server`, redirect 301, `/.well-known/acme-challenge/`.
- [ ] `deployment/compose/docker-compose.prod.yml`: comando do certbot (escape `$$`, wait do token), volumes, projeto `-p siscom`.
- [ ] `deployment/scripts/smoke.sh`: dual-scheme (https/http) — parse dos helpers `get`/`post`.

## 5. Frontend — revisar

- [ ] `frontend/src/api/client.ts`: `ImagemProduto` sem `url_origem`; `aplicarImagensLote` com `deduplicadas` opcional.
- [ ] `frontend/src/pages/produtos.tsx`: lista (sku+detalhe), `ModalImagensLote`, mensagens dedup.
- [ ] `frontend/public/demo-publico.html`: JS (sem framework) — busca, filtros (grupo/cat/subcat/marca), paginação, modal detalhe, escape HTML.

## 6. Melhorias/pendências que podem esconder bugs de dados

- [ ] **~4.275 produtos sem `grupo_id`** (fios desmembrados na unificação) — não aparecem no filtro por grupo.
- [ ] **~3.215 produtos sem imagem** — não há vínculo no filesystem; verificar se algum arquivo em `images/cadastro/<id>/` ficou órfão (sem linha) ou linha sem arquivo.
- [ ] `FERRAGENS`: não existe como grupo (há PAR=PARAFUSOS). Confirmar se é renomear ou criar.

---

## Resultado da análise

| Área | Status | Bugs encontrados / correções |
|---|---|---|
| 1. Imagens | ✅ | Sem regressão estrutural encontrada nesta revisão; manter teste de filesystem real. |
| 2. API pública | ✅ | CORS passou a aceitar somente origens configuradas; site não publica catálogo demonstrativo no SSR. |
| 3. Imagens lote | ✅ | Fluxo passa na suíte; falta cobertura de sites reais/HTML dinâmico. |
| 4. TLS/nginx | ✅ | Staging usa o certificado compartilhado em somente-leitura na porta dedicada `:444` para webhooks; healthcheck produtivo usa credenciais do ambiente. |
| 5. Frontend | ⚠️ | Code-splitting, modularização, cache, validação runtime mínima e Error Boundary OK; permanecem virtualização e testes E2E. |
| 6. Dados | ✅ | Outbox com claim/lease e baixa de pagamentos com conta+caixa na mesma transação. |

### Auditoria RBAC — 2026-08-30

**Status: ✅ corrigido no código; requer validação em staging antes da release.**
Além do mapeamento das 366 rotas `/api`, a ação efetiva e a segregação de funções
agora são aplicadas no backend e cobertas por testes de regressão. Os achados
originais foram:

1. **P1 — escalação de privilégio:** endpoints de criação/edição de usuários e
   de atribuição de perfis/overrides permitem que qualquer papel com
   `usuarios.editar` atribua Administrador ou conceda ações superiores, sem
   limite pela alçada do ator.
2. **P1 — emissão fiscal:** NFC-e/NF-e/Focus não possuem permissão explícita e
   caem no genérico `orcamentos.cadastrar`; vendedor/operador podem alcançar a
   emissão se as demais validações de negócio passarem.
3. **P1 — fluxo de desconto:** rejeitar desconto não verifica
   `orcamentos.aprovar`/`autoriza_desconto`, permitindo que perfis de venda
   rejeitem solicitações fora da segregação esperada.
4. **P1 — revogação pelo cadastro:** o formulário envia `perfil_ids: []` e
   overrides vazios; o backend interpreta o primeiro como Vendedor e não limpa
   o segundo, mantendo acessos que o administrador tentou remover.
5. **P1/P2 — continuidade administrativa:** não há proteção transacional contra
   remover/desativar todos os administradores, nem auditoria de alterações de
   perfis, matriz e overrides.
6. **P2 — sessão e tokens:** logout não revoga tokens HMAC de sete dias, e
   registros de autoria usam `flask.session` em vários endpoints apesar da
   autenticação ser Bearer.
7. **P2 — UX de autorização:** o frontend filtra somente `visualizar`; ações
   de cadastrar/editar/excluir/aprovar/configurar/imprimir continuam visíveis e
   falham apenas depois no backend.

Validação desta auditoria: `21 passed` em `test_permissao.py` +
`test_hardening.py`; `34 passed` no frontend e `typecheck` concluído. As
correções posteriores adicionaram as migrações `0103`/`0104`, testes de regressão
e passaram em `248 passed` no backend, além de `34 passed`, `typecheck` e `build`
no frontend. Nenhum deploy, restart ou migração não-dev foi executado.

### Achados prioritários desta revisão — situação

1. **Resolvido:** baixa financeira, outbox, retry, healthcheck, TLS dedicado por porta, SSR do site, emissão concorrente e payload webhook.
2. **Pendente:** validação live do webhook externo no staging e TLS/roteamento da produção permanecem operações separadas.
3. **RBAC corrigido:** atribuição privilegiada, emissão fiscal, segregação de
   desconto, revogação vazia, último administrador, revogação de tokens, autoria
   Bearer, auditoria e gates de ações críticas foram tratados. Permanecem a
   validação live em staging, testes E2E dos fluxos críticos e virtualização de
   tabelas extensas; cache e validação runtime mínima já entregues.

Validação atual: `248 passed` no backend em banco dev isolado; `34 passed`,
`typecheck` e `build` no frontend; build Astro do site passou e a home não
contém produto demonstrativo. Nenhum deploy, restart ou migração não-dev foi
executado.

> Ao finalizar: atualize `CONTEXTO_SESSAO.md` (log + pendências) e faça commit/push.

## Resultado da auditoria do Plano Mestre — 2026-09-01

Foi realizada revisão estática das ondas implementadas até a migração 0142 e
execução dos testes frontend e dos módulos backend mais recentes. O resultado
detalhado está em `RELATORIO_AUDITORIA_PLANO_MESTRE_ERP.md`.

Status: **PENDENTE DE CORREÇÕES P0/P1**.

Achados confirmados:

- ABC histórica usa critério `consumo` inexistente nas métricas, não isola
  depósito e `aplicar()` sobrescreve a classe global.
- Recebimento cria conta a pagar fixa em 30 dias, ignora condição, pode duplicar
  títulos em recebimento parcial e engole falha contábil.
- Conciliação bancária sempre atualiza `contas_receber`, inclusive matching de
  contas a pagar.
- APIs de compras/recebimento aceitam ator (`usuario_id`, `operador_id` e
  `aprovador_id`) enviado pelo cliente.
- Motor de reposição mistura trânsito/demanda entre depósitos e não desconta
  recebimento parcial.
- Idempotência central conflita chaves de escopos diferentes e não trata
  exceção com contexto transacional correto.
- Relatórios novos têm agrupamentos quebrados, escopo incompleto e não atendem
  paginação/filtros/exportação/drill-down do plano.
- OpenAPI e schemas não cobrem os endpoints recentes; XML de entrada não fecha
  o pipeline com recebimento/financeiro.

Verificação: frontend `typecheck` e 39 testes passaram; backend direcionado
(`test_abc_historica.py`, `test_motor_reposicao.py`, `test_infra.py`,
`test_recebimento_documento.py`, `test_relatorios.py`) passou com 37 testes.
A suíte backend integral não foi declarada como aprovada nesta auditoria.

## Correção do fluxo de release — 2026-09-05

Status: **✅ corrigido no código; nenhum deploy executado.**

- [x] Staging completo cria tag candidata anotada somente depois de todos os gates.
- [x] Produção seleciona automaticamente a RC pendente mais recente e valida run, tentativa, workflow, SHA e manifesto.
- [x] Candidata de produção deve pertencer ao histórico de `main`.
- [x] Produção promove os mesmos IDs de imagem testados, sem rebuild.
- [x] Componentes são derivados do manifesto e a tag final nasce após os gates produtivos.
- [x] Histórico registra exclusivamente a versão promovida.

Validação: `actionlint` nos dois workflows e 27 testes backend combinados, incluindo
6 testes do controle de release; `py_compile`, JSON do manifesto e Compose verdes. O próximo
passo operacional é o próprio usuário executar staging completo com incremento
`patch` e, se verde, clicar no workflow de produção sem informar tag.

## Correção da leitura de códigos no PDV — 2026-09-05

Status: **✅ corrigido e validado no DEV; nenhum deploy executado.**

- [x] Pré-venda usa a busca rápida que inclui `produto_identificador` ativo.
- [x] Enter imediato do leitor não depende do debounce de sugestões.
- [x] Código exato único adiciona o produto e devolve foco para a próxima leitura.
- [x] Código ambíguo exige seleção; sugestões antigas não são lançadas.
- [x] Busca exclui produto inativo e devolve imagem, NCM e descrição ao PDV.
- [x] OpenAPI, manual e testes backend/frontend atualizados.

Evidência local: EAN adicional `7899674038869` encontrou o produto 9965 e o
incluiu por `R$ 420,82`; 18 testes backend e 49 frontend passaram.

## Correção do 502 local após rebuild — 2026-09-05

Status: **✅ corrigido e validado no DEV; nenhum deploy executado.**

- [x] Confirmado que backend e `/api/pronto` estavam saudáveis.
- [x] Identificado IP obsoleto do Vite mantido pelo Nginx após recriação.
- [x] Upstream do Vite alterado para resolução dinâmica pelo DNS Docker.
- [x] Configuração validada com `nginx -t` e raiz novamente em HTTP 200.
- [x] Vite recriado isoladamente; após a janela de inicialização, a raiz voltou
  automaticamente a 200 sem reload/restart do Nginx.
