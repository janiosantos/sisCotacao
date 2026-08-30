# Plano de Execucao das 8 Pendencias

Este plano organiza as oito pendencias por prioridade. A execucao e sequencial:
uma etapa so muda para concluida depois do criterio de aceite e do gate de
seguranca correspondente. Nenhum deploy, restart, migracao fora de DEV ou
exclusao de arquivos e disparado automaticamente.

## 1. Schema e staging

- **Status:** pronta para execucao autorizada.
- **Escopo:** aplicar as migracoes `0097` e `0098` em staging, executar testes
  de migracao banco vazio -> head, testes backend/frontend e smoke tests.
- **Pre-requisitos:** `APP_VERSION`, credenciais do banco, `CATALOG_SECRET` e
  segredos dos webhooks configurados no ambiente de staging.
- **Aceite:** health check, smoke test, login com rate limit, emissao sandbox
  de cobranca e rollback documentado.
- **Bloqueio atual:** requer autorizacao explicita para iniciar o workflow.

## 2. Webhooks e segredos de provedores

- **Status:** protecao generica implementada; assinatura nativa pendente.
- **Escopo:** configurar os segredos de webhook e validar assinatura oficial
  de cada provedor, com rejeicao de replay e idempotencia por evento.
- **Pre-requisitos:** documentacao/credenciais de Asaas, Mercado Pago, EfiPay,
  Sicoob e TecnoSpeed; confirmar headers e formato de assinatura.
- **Aceite:** fixture valido processa uma vez; assinatura invalida, payload
  antigo ou evento repetido nao baixa a mesma conta novamente.

## 3. Fiscal NF-e/NFC-e e homologacao

- **Status:** estrutural, nao pronto para producao.
- **Escopo:** completar XSD, assinatura A1/A3, chave com data real,
  destinatario/IBGE, CST/CSOSN/PIS/COFINS/ST e regras IBS/CBS vigentes.
- **Pre-requisitos:** contador/responsavel fiscal, certificado, ambiente
  Focus/SEFAZ, matriz fiscal confirmada e fontes oficiais versionadas.
- **Aceite:** casos fiscais golden aprovados, XML validado e assinado,
  autorizacao em homologacao, cancelamento/contingencia testados e auditoria
  do snapshot explicavel.
- **Regra:** `FISCAL_ENGINE_V2` permanece desligada em producao ate o aceite.

## 4. Site institucional

- **Status:** bloqueada por artefato ausente.
- **Escopo:** disponibilizar o projeto `CASA_LM/site`, apontar `siteConfig.ts`
  para `/api/publico/*`, consumir `has_more` e validar busca/filtros.
- **Aceite:** build do site, CORS restrito aos dominios aprovados, pagina inicial
  e catalogo funcionando em desktop/mobile.
- **Bloqueio atual:** este checkout nao contem `CASA_LM/site`.

## 5. Outbox e processamento assincrono

- **Status:** planejamento tecnico pendente.
- **Escopo:** criar outbox transacional para cobrancas, webhooks, imagens e
  integracoes externas; adicionar worker, retry com backoff, dead-letter,
  observabilidade e chaves de idempotencia.
- **Pre-requisitos:** definir provedor do worker (Celery/RQ), Redis ou broker,
  limites de retry e quais operacoes podem sair do request HTTP.
- **Aceite:** falha externa nao desfaz o fato de negocio, reprocessamento e
  seguro, duplicatas sao ignoradas e itens mortos aparecem para operador.

## 6. Frontend, performance e testes E2E

- **Status:** parcialmente iniciado.
- **Escopo:** modularizar telas grandes, adicionar cache/query client e schemas
  runtime, virtualizar tabelas extensas e ampliar testes de fluxos criticos.
- **Pre-requisitos:** definir contrato de erro da API e paginas prioritarias:
  PDV, estoque, financeiro, compras e fiscal.
- **Aceite:** typecheck/build limpos, cobertura dos fluxos principais, loading,
  empty/error states e sem regressao mobile/tablet.

## 7. TLS e sincronizacao de ambientes

- **Status:** procedimento documentado, execucao operacional pendente.
- **Escopo:** emitir Let's Encrypt via DNS-01 Cloudflare, revisar roteamento
  443, validar renovacao e sincronizar a VM com git/pull e a release aprovada.
- **Pre-requisitos:** token Cloudflare Zone:DNS:Edit, acesso ao roteador/VM,
  backup e autorizacao explicita de deploy/restart.
- **Aceite:** HTTPS valido, renovacao verificada, `/api/health` e smoke test
  executados na VM e staging.

## 8. Saneamento de imagens e arquivos

- **Status:** aguardando confirmacao de exclusao.
- **Escopo:** revisar os produtos sem imagem, executar lote por fornecedor e
  somente depois remover arquivos/pastas orfas identificados.
- **Pre-requisitos:** backup, relatorio dry-run com contagem e lista de paths,
  aprovacao do responsavel e janela de manutencao.
- **Aceite:** nenhum produto ativo perde imagem, relatorio antes/depois salvo,
  rollback por backup disponivel.

## Gate de transicao

Cada etapa deve registrar no `CONTEXTO_SESSAO.md` status, evidencias, risco e
proximo passo. A etapa seguinte nao deve ser iniciada se o aceite anterior ou
seu plano de rollback estiver ausente.
