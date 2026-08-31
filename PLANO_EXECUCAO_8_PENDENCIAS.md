# Plano de Execucao das 8 Pendencias

Este plano organiza as oito pendencias por prioridade. A execucao e sequencial:
uma etapa so muda para concluida depois do criterio de aceite e do gate de
seguranca correspondente. Nenhum deploy, restart, migracao fora de DEV ou
exclusao de arquivos e disparado automaticamente.

> **Status atualizado em 2026-08-30** — cruzado com `CONTEXTO_SESSAO.md` e
> `git log`. O que esta `[x]` ja foi executado/validado (em DEV e/ou STAGING,
> salvo indicacao). **PRODUCAO continua sem deploy das mudancas recentes** —
> so recebe release aprovada com confirmacao explicita do usuario.

## 1. Schema e staging

- **Status:** [x] concluida.
- **Escopo:** aplicar as migracoes `0097` e `0098` em staging, executar testes
  de migracao banco vazio -> head, testes backend/frontend e smoke tests.
- **Pre-requisitos:** `APP_VERSION`, credenciais do banco, `CATALOG_SECRET` e
  segredos dos webhooks configurados no ambiente de staging.
- **Aceite:** health check, smoke test, login com rate limit, emissao sandbox
  de cobranca e rollback documentado.
- **Evidencias (2026-08-30):** secrets configurados no GitHub
  (`CATALOG_SECRET`, `POSTGRES_USER`/`POSTGRES_PASSWORD`); deploy Staging
  validado (run 33293628345 — migracoes 0097/0098 em banco vazio->head, smoke,
  rate limit). Schema no DEV: **102** (0097 cobranca_ambiente,
  0098 login_rate_limit, 0099 webhook_secret, 0100 webhook_log, 0101 outbox,
  0102 outbox_claim).

## 2. Webhooks e segredos de provedores

- **Status:** [x] concluida.
- **Escopo:** configurar os segredos de webhook e validar assinatura oficial
  de cada provedor, com rejeicao de replay e idempotencia por evento.
- **Pre-requisitos:** documentacao/credenciais de Asaas, Mercado Pago, EfiPay,
  Sicoob e TecnoSpeed; confirmar headers e formato de assinatura.
- **Aceite:** fixture valido processa uma vez; assinatura invalida, payload
  antigo ou evento repetido nao baixa a mesma conta novamente.
- **Evidencias (2026-08-30):** assinatura/token nativo por provedor
  (MP x-signature HMAC-SHA256 + anti-replay por `ts`; Asaas `asaas-access-token`;
  EfiPay `?token=`; Sicoob/TecnoSpeed `X-Webhook-Secret`), migracao 0099
  (`webhook_secret`), tabela `webhook_log` (0100) com logs/detalhe/rechecagem
  (`GET /api/webhooks/logs`, `POST /api/webhooks/rechecagem`) e tela Webhooks.
  **Validado em staging**: baixa por notificacao (Asaas sandbox pix/boleto),
  token real -> 200, errado/sem -> 401, provider nao configurado -> 503,
  rechecagem 200, log de `nao_autorizado`. Bug corrigido: caixa com `PgRow`
  (`0173d44`). **Pendencia menor:** reativar a fila do webhook no Asaas sandbox
  (apos 15 falhas) e revalidar entrega real.

## 3. Fiscal NF-e/NFC-e e homologacao

- **Status:** [ ] bloqueada por artefato externo (certificado + contador).
- **Escopo:** completar XSD, assinatura A1/A3, chave com data real,
  destinatario/IBGE, CST/CSOSN/PIS/COFINS/ST e regras IBS/CBS vigentes.
- **Pre-requisitos:** contador/responsavel fiscal, certificado, ambiente
  Focus/SEFAZ, matriz fiscal confirmada e fontes oficiais versionadas.
- **Aceite:** casos fiscais golden aprovados, XML validado e assinado,
  autorizacao em homologacao, cancelamento/contingencia testados e auditoria
  do snapshot explicavel.
- **Regra:** `FISCAL_ENGINE_V2` permanece desligada em producao ate o aceite.
- **Situacao real (2026-08-30):** permanece como estava — codigo estrutural,
  sem XSD/assinatura/homologacao. Lista de pendentes fiscais em `PENDENCIAS.md`.

## 4. Site institucional

- **Status:** [x] integração de código concluída; validação live pendente.
- **Escopo:** disponibilizar o projeto `CASA_LM/site`, apontar `siteConfig.ts`
  para `/api/publico/*`, consumir `has_more` e validar busca/filtros.
- **Aceite:** build do site, CORS restrito aos dominios aprovados, pagina inicial
  e catalogo funcionando em desktop/mobile.
- **Situacao real (2026-08-30):** o projeto **existe** em
  `C:\Users\jpsantos\Documents\Projetos\CASA_LM\site` (repo `janiosantos/casa-lm-site`,
  Astro). `api.ts` usa `PUBLIC_API_ORIGIN`; o fallback demonstrativo ficou
  restrito ao navegador e a home gerada no SSR nao publica dados demo. O
  backend restringe CORS por `PUBLIC_CORS_ORIGINS`. Build Astro validado;
  falta somente validacao live apos publicacao.

## 5. Outbox e processamento assincrono

- **Status:** [x] fundacao + outbox transacional concluidas.
- **Escopo:** outbox transacional para cobrancas, webhooks, imagens e
  integracoes externas; retry com backoff, dead-letter, observabilidade e
  chaves de idempotencia.
- **Pre-requisitos:** worker RQ + Redis (decisao tomada); definir quais
  operacoes saem do request HTTP e o contrato de reprocessamento.
- **Aceite:** falha externa nao desfaz o fato de negocio, reprocessamento e
  seguro, duplicatas sao ignoradas e itens mortos aparecem para operador.
- **Evidencias (2026-08-30):** Redis + worker RQ + scheduler nos 3 composes;
  rechecagem periodica (`RECHECAGEM_INTERVAL_MIN`, default 15) e `rodar_outbox`
  (`OUTBOX_INTERVAL_SEC`, default 60); tabela **`outbox`** (migracoes 0101 e
  0102) com `topico/payload/status/tentativas/proxima_tentativa/ultimo_erro/
  idempotencia_key` e lease de processamento (`processando_em/processando_por`);
  backoff exponencial 60s·2ⁿ, dead-letter apos 5 tentativas; consumidor
  `webhook.rechecagem`; **webhook 503 enfileira a rechecagem da conta**
  (idempotente `webhook:provider:payment_id`). Endpoints
  `GET /api/webhooks/outbox`, `POST /api/webhooks/outbox/rodar`. Validado em
  staging (webhook efipay sem config -> 503 -> outbox -> worker processou -> ok).
  A implementacao tambem faz claim atomico com `SKIP LOCKED`, recupera leases
  expirados e transforma payload/resultado invalido em retry, sem falso sucesso.

## 6. Frontend, performance e testes E2E

- **Status:** [x] modularizacao concluida; **divida residual** (performance/E2E).
- **Escopo:** modularizar telas grandes, adicionar cache/query client e schemas
  runtime, virtualizar tabelas extensas e ampliar testes de fluxos criticos.
- **Pre-requisitos:** definir contrato de erro da API e paginas prioritarias:
  PDV, estoque, financeiro, compras e fiscal.
- **Aceite:** typecheck/build limpos, cobertura dos fluxos principais, loading,
  empty/error states e sem regressao mobile/tablet.
- **Evidencias (2026-08-30):** **P6 concluida — 29 telas modularizadas, 93
  modulos** em 26 pastas (financeiro, produtos, compras, fiscal, pre-venda,
  precos, orcamentos, caixa, estoque, configuracoes, cotacoes, catalogo,
  posvenda, bancos, atualizacoes, historico, dashboard, clientes, fornecedores,
  usuarios, perfis, unidades, vendedores, plano_contas, solicitacoes,
  diagnostico_variacoes). Contrato de erro `ApiError` + `mensagemErro`.
  **27 testes frontend** (era 13) + typecheck/build verdes. Corrigido mojibake
  (double-encoding cp1252) em todo o frontend (dry-run = 0).
  **Divida residual do P6:** query client/cache, schemas runtime, virtualizacao
  de tabelas extensas e testes E2E de fluxos criticos.

## 7. TLS e sincronizacao de ambientes

- **Status:** [x] concluida para isolamento de ambientes; staging usa HTTPS
  em porta dedicada e TLS publico de producao continua pendente de publicacao.
- **Escopo:** emitir Let's Encrypt via DNS-01 Cloudflare, revisar roteamento
  443, validar renovacao e sincronizar a VM com git/pull e a release aprovada.
- **Pre-requisitos:** token Cloudflare Zone:DNS:Edit, acesso ao roteador/VM,
  backup e autorizacao explicita de deploy/restart.
- **Aceite:** HTTPS valido, renovacao verificada, `/api/health` e smoke test
  executados na VM e staging.
- **Evidencias (2026-08-30):** staging permanece isolado por projeto Docker e
  banco/rede próprios, usa HTTP `:8081` e HTTPS `:444` com o mesmo certificado
  do domínio em volume somente-leitura, necessário aos webhooks externos. O
  compose de produção tem healthcheck parametrizado por
  `POSTGRES_USER/POSTGRES_DB`; deploy/TLS da produção continuam sujeitos a
  autorização.
  **Pendente de operacao autorizada:** ativar/confirmar o roteamento do TLS no
  dominio de producao (porta 443 interna + `compose up -d --build`).

## 8. Saneamento de imagens e arquivos

- **Status:** [~] dry-run concluido; **aguardando confirmacao de exclusao**.
- **Escopo:** revisar os produtos sem imagem, executar lote por fornecedor e
  somente depois remover arquivos/pastas orfas identificados.
- **Pre-requisitos:** backup, relatorio dry-run com contagem e lista de paths,
  aprovacao do responsavel e janela de manutencao.
- **Aceite:** nenhum produto ativo perde imagem, relatorio antes/depois salvo,
  rollback por backup disponivel.
- **Evidencias (2026-08-30):** dry-run commitado em `reports/*` — **3.188
  produtos sem imagem** (3.181 ativos), 0 linhas quebradas, **5.648 arquivos
  orfaos (435 MB)** e **2.742 pastas orfas (1.060 MB)**; nenhum sem-imagem tem
  arquivo orfao (precisa lote por fornecedor). **Tarefa deixada pendente pelo
  usuario** (aguarda aprovacao para lote + remocao).

## Gate de transicao

Cada etapa deve registrar no `CONTEXTO_SESSAO.md` status, evidencias, risco e
proximo passo. A etapa seguinte nao deve ser iniciada se o aceite anterior ou
seu plano de rollback estiver ausente.

**Proximo passo sugerido:** P8 (aprovar lote por fornecedor + remocao de
orfao) ou divida residual do P6 (query client/cache + E2E). P3 depende de
certificado/contador externos.
