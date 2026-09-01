# Backup e continuidade (ADM-004)

## Objetivo
Backup automatizado de **PostgreSQL + imagens + configurações + outbox** com
retenção, criptografia, teste de restauração em ambiente isolado, RPO/RTO
documentados e evidência. Banco e arquivos devem ser consistentes (mesmo ponto
no tempo).

## Ferramenta
`scripts/backup.py` — gera por execução:

```
backup-<timestamp>/
  schema.dump      (pg_dump --schema-only)
  data.dump        (pg_dump)
  images.tar.gz    (imagens de produtos, se informadas)
  manifest.json    (hash SHA-256 de cada arquivo)
```

- **Retenção**: mantém os N backups mais recentes (padrão 7).
- **Consistência**: banco e imagens ficam no mesmo diretório/execução.

## Uso
```bash
python scripts/backup.py --dir ./backups --reter 7 \
  --pg-url 'postgresql://user:senha@host:5432/db' --images ./images
```

## Procedimento
1. **Agendamento**: pipeline/agendador dispara `backup.py` fora do processo web
   (credenciais via secret manager, nunca em código).
2. **Teste de restauração**: em ambiente isolado, `pg_restore` do `data.dump` +
   `schema.dump` e conferência de contagens (origem/destino).
3. **Criptografia**: os dumps são criptografados no destino de backup
   (bucket/volume) conforme política; as chaves fora do repositório.
4. **Evidência**: `manifest.json` (hash) + log da execução.

## RPO / RTO (padrão sugerido)
- **RPO**: ≤ 1 dia (backup diário) — pode ser reduzido com PITR/WAL arquivado.
- **RTO**: ≤ 2h para restauração de banco + imagens em ambiente isolado.

## Restauração (isolado)
```bash
pg_restore --no-owner -d banco_teste backup-<ts>/schema.dump
pg_restore --no-owner -d banco_teste backup-<ts>/data.dump
```

## Regra
Backup/restauração **nunca depende de acesso manual a produção**; produção não
é tocada por este script diretamente — o pipeline orquestra com aprovação.