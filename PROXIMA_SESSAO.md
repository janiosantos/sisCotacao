# Retomada — próxima sessão

> ⚠️ **Este arquivo está obsoleto** (era o plano da migração para Tailwind, concluída
> há várias releases — todas as telas estão em React + Tailwind e a P6 modularizou
> as 29 telas). **Use `CONTEXTO_SESSAO.md` (estado/pendências) e
> `PLANO_EXECUCAO_8_PENDENCIAS.md` (status das 8 pendências)** como referência atual.

## Estado atual (resumo 2026-08-30)

- **Schema dev/staging**: 101 (0097..0101). Produção em v2.32.2 (sem deploy recente).
- **8 pendências**: P1/P2/P5/P7 concluídas; P6 modularização concluída (93 módulos,
  27 testes frontend; residual: cache/E2E); P4 em andamento (`CASA_LM/site`);
  P8 dry-run pronto (aguarda aprovação para remoção); P3 bloqueada (certificado/contador).
- **Hardening** (RBAC deny-default, SSRF, rate limit, segredos) validado em staging.
- **Acesso ao servidor (staging)**: SSH `root@10.189.14.8` (chave `id_rsa`), repo
  persistente `/home/jpsantos/siscom/repo`. Deploy direto: `git pull && docker compose
  -p siscom-staging -f deployment/compose/docker-compose.staging.yml up -d --build <svc>
  && versioning apply`. Login staging: `admin/admin123`.

## Próximos passos (ordem sugerida)

1. P8 — aprovar lote de imagens por fornecedor + remoção de órfãos (dry-run em `reports/*`).
2. P6 residual — query client/cache, schemas runtime, virtualização de tabelas, testes E2E.
3. P4 — apontar `siteConfig.ts` do `CASA_LM/site` + CORS restrito.
4. Publicação autorizada — release hardening + P2/P5/P6 em produção.
5. P3 fiscal — desbloquear com certificado A1/A3 + contador.