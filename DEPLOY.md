# Deploy em produção (siscom)

Pipeline de deploy com **GitHub Actions + self-hosted runner** no próprio servidor.
Imagens são buildadas **no servidor** (sem registry, sem transferência de ~90MB); o
banco **nunca para** (migrações aplicadas online no startup do backend). Dados de
produção **nunca são sobrescritos** por dump/restore.

## Visão geral
- Trigger: `git tag vX.Y.Z` + `git push --tags` (ou `workflow_dispatch` manual).
- Runner `siscom-prod` (instalado no servidor) executa `.github/workflows/deploy.yml`:
  1. `checkout`
  2. Se houver migration **pendente**, faz `pg_dump` de segurança em
     `/home/jpsantos/siscom/backups/prod-pre-<timestamp>.dump`
  3. `docker compose build` (incremental, cache de layers)
  4. `docker compose up -d` (backend sobe e aplica migrações online; volume
     `siscom_postgres-data` preservado → dados intactos)
  5. Health gate: `pg_migrations status` + `curl` em `/api/health` no backend (até 30×3s)
  6. `docker image prune -f`
- Rollback de imagem: `docker tag siscom-backend:prev siscom-backend:latest &&
  docker compose -f docker-compose.prod.yml up -d`

## Setup one-time (servidor)
Gerar token em GitHub → `janiosantos/sisCotacao` → Settings → Actions → Runners →
New runner. Depois, no servidor:
```bash
bash scripts/ci/setup-runner.sh <runner_registration_token>
# verificar: GitHub → Settings → Actions → Runners → "siscom-prod" Idle
```
(O token de registro expira em ~1h; se expirar, gere um novo.)

## Fazer um deploy
1. **Mudança de estrutura** = nova migration em `scripts/pg_migrations/versions/0061_*.py`
   (nunca editar 0052–0060). Ver abaixo o padrão.
2. Commitar e subir para `main`/branch.
3. Taggear e empurrar:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. Acompanhar em GitHub → Actions → job `deploy` (roda no servidor).

## Padrão de migração (importante)
- **Idempotente**: `DROP COLUMN IF EXISTS`, `CREATE TABLE IF NOT EXISTS`,
  `CREATE INDEX IF NOT EXISTS`; `guard` deve detectar estado parcial.
- **DROP COLUMN / RENAME**: seguros (app não atende durante o restart do container).
  O novo código não deve referenciar o objeto removido.
- **ALTER TYPE / remodelagem**: usar **expand/contract**:
  - *Expand:* criar nova coluna/tabela + backfill em lotes (evita lock longo).
  - *Contract:* após estabilizar, dropar o antigo em migration separada.
- `forward` de `.py` deve iniciar com `conn.autocommit = True` se usar
  `CREATE INDEX ... CONCURRENTLY`.
- Falha parcial é coberta por: idempotência + `pg_dump` prévio + rollback de imagem.
- O runner trata exceção em `guard` como "não aplicada" (não derruba o startup).

## Verificar estado do banco (controle de update)
```bash
# dentro do container backend em produção:
docker compose -f docker-compose.prod.yml exec backend \
  python -m scripts.pg_migrations status    # versões aplicadas/pendentes + checksum
docker compose -f docker-compose.prod.yml exec backend \
  python -m scripts.pg_migrations plan      # pendentes que serão aplicadas
docker compose -f docker-compose.prod.yml exec backend \
  python -m scripts.pg_migrations check     # conexão + pendentes
```

## Rollback
- Deploy falhou no health gate: o pipeline não sobe a nova versão; para reverter
  manualmente ao estado anterior:
  ```bash
  docker tag siscom-backend:prev siscom-backend:latest
  docker compose -f docker-compose.prod.yml up -d
  ```
- Se uma migration destrutiva corrompeu o banco: restaurar o `pg_dump` de
  `/home/jpsantos/siscom/backups/prod-pre-*.dump` (restaura dados + schema).

## ⚠️ Aviso sobre os dados atuais
O deploy manual anterior (dump/restore) já sobrescreveu o banco de produção com o
dump de **dev**. A política "produção é live / não sobrescrever" vale **a partir
deste pipeline**. Se for necessário popular produção com dados reais, use o fluxo
normal de importação do ERP (nunca dump/restore destrutivo).

## Scripts antigos (deprecados)
- `deploy-db.bat` — desativado (dump/restore destrutivo de 106MB).
- `deploy-prod.bat` — mantido apenas como fallback manual (build no servidor via SSH).
