# Deploy em produção (siscom)

Pipeline de deploy com **GitHub Actions + self-hosted runner** no próprio servidor.
As imagens são construídas e testadas no staging e depois promovidas com o mesmo
ID de conteúdo para produção, sem registry ou rebuild. Migrações são executadas em uma
etapa explícita, fora do startup da aplicação. Dados de produção nunca são
sobrescritos por dump/restore.

## Visão geral
- A publicação é sempre manual por `workflow_dispatch`; criar ou enviar uma tag
  manualmente não dispara deploy.
- Staging completo cria automaticamente a tag anotada
  `vX.Y.Z-rc.<GITHUB_RUN_ID>.<TENTATIVA>` somente depois de migrations, testes, build,
  health, impressão, smoke e reconciliação ficarem verdes.
- Produção seleciona automaticamente a tentativa mais recente do único ciclo
  candidato ainda não publicado, consulta o run pela API do GitHub, confirma
  workflow, conclusão e SHA, valida o manifesto e promove as mesmas imagens.
- Se houver migration pendente, faz `pg_dump` em
  `/home/jpsantos/siscom/backups/prod-pre-<timestamp>.dump` antes da aplicação.
- A tag final `vX.Y.Z` é criada automaticamente somente depois de health, worker
  de impressão, smoke e registro do histórico ficarem verdes.
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

O repositório pode manter **Settings → Actions → General → Workflow permissions**
em somente leitura. Os workflows solicitam de forma explícita e limitada apenas
`contents: write` para criar tags e, na produção, `actions: read` para validar o
run de staging. Em **Settings → Environments → production**, opcionalmente
configure seu próprio usuário como aprovador; nesse caso haverá uma confirmação
adicional antes de qualquer operação produtiva.

## Fazer um deploy sem depender de terminal ou agente
1. Garanta que a mudança e o manifesto da próxima versão estejam commitados no `main`.
2. Abra **GitHub → Actions → Deploy Staging (siscom) → Run workflow**.
3. Em **Use workflow from**, escolha `main`; selecione apenas o incremento
   `patch`, `minor` ou `major`, mantenha `completo` e execute.
4. O workflow calcula a versão e mostra no Summary a candidata criada, por
   exemplo `v2.40.1-rc.33999999999.1`. Não é preciso copiar ou digitar a tag.
5. Abra **GitHub → Actions → Deploy produção (siscom) → Run workflow**, escolha
   `main` em **Use workflow from** e apenas clique em **Run workflow**.
6. A produção seleciona e valida automaticamente a RC aprovada mais recente.
   Ao final, a tag definitiva `vX.Y.Z` estará criada e o
   painel **Admin → Atualizações** mostrará apenas essa release.

O modo `rapido` atualiza o staging para testes exploratórios, mas não roda a suíte
completa e, por segurança, **não cria tag candidata promovível**.

### Como a versão é incrementada

A fonte da verdade é a maior tag final no formato estrito `vMAJOR.MINOR.PATCH`.
Tags antigas com sufixos livres, como `v1.6.4-estavel`, não entram no cálculo.
Partindo de `v2.40.0`:

| Incremento selecionado | Versão calculada |
|---|---|
| `patch` | `v2.40.1` |
| `minor` | `v2.41.0` |
| `major` | `v3.0.0` |

Durante o desenvolvimento, o responsável pode consultar antecipadamente o nome
do manifesto sem criar tags nem alterar ambientes:

```bash
python scripts/release_control.py next --bump patch
```

O staging exige que `releases/<versão-calculada>.json` exista e corresponda à
versão e às imagens esperadas. Só pode existir um ciclo de RC não publicado por
vez; novas tentativas do mesmo ciclo são permitidas e produção escolhe a de maior
`run_id/tentativa`. Isso elimina listas estáticas e entradas livres: o GitHub
Actions não suporta preencher dinamicamente opções de um dropdown a partir das
tags durante a abertura do formulário.

## Padrão de migração (importante)
- **Classificação de risco**: todo arquivo `.py` declara `RISCO` no topo:
  `"critica"` (estrutura central / recria tabela / altera dados em massa),
  `"melhoria"` (funcionalidade aditiva, não-quebrante),
  `"rotina"` (seed idempotente / ajuste pequeno) ou `"n/c"` (ausente).
  O `pg_migrations status`/`plan` exibem o risco; o valor é persistido em
  `schema_migrations.risco`. Use para destacar atualizações críticas x melhorias.
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
  python -m migrations status    # versões aplicadas/pendentes + checksum
docker compose -f docker-compose.prod.yml exec backend \
  python -m migrations plan      # pendentes que serão aplicadas
docker compose -f docker-compose.prod.yml exec backend \
  python -m migrations check     # conexão + pendentes
```

## Manutenção automatizada (tarefas de dados)

Operações em produção **sem `scp` manual**: o runner `siscom-prod` executa o
módulo `catalog_server.maintenance` dentro do container `backend` via
`.github/workflows/maintenance.yml` (disparado por `workflow_dispatch`).

Como usar:
1. GitHub → Actions → **Manutenção produção (siscom)** → Run workflow.
2. Escolha a `task` no menu e confirme.
3. O log do job traz a saída da tarefa rodando no servidor.

Tarefas disponíveis (`python -m catalog_server.maintenance <task>`):
- `health` — resumo do estado do catálogo (contagens de produtos/variantes/FTS).
- `diagnose_search` — valida que produtos **com atributos** retornam na busca FTS
  (amostra 15 produtos; reporta falhas). Somente-leitura.
- `fts_rebuild` — reconstrói `produtos_fts` a partir das tabelas base (índice
  derivado/regenerável; **não** altera dados de origem). Use após a normalização
  / re-importação do catálogo.

Para adicionar uma tarefa: crie a função em `catalog_server/maintenance.py`,
registre em `TASKS` e adicione a opção no input `task` de `maintenance.yml`.

## Versionamento do sistema (app ↔ schema)

O backend expõe `GET /api/sistema/status` com a visão unificada de versão:

- `app_version` — vem de `APP_VERSION` (injeto no build a partir do `git tag`;
  `dev` em ambiente local).
- `schema_version` / `schema_max` — versão aplicada e máxima das migrações.
- `pending` / `pending_por_risco` — migrações pendentes agrupadas por
  `RISCO` (`critica` / `melhoria` / `rotina` / `n/c`).

A resposta é **somente-leitura** (consulta `schema_migrations`; não aplica
migrações). O deploy define `APP_VERSION` automaticamente via `git describe`
(`deploy.yml` → step "Resolve versão da imagem").

Exemplo:
```json
{
  "app_version": "v1.2.0",
  "schema_version": 60,
  "schema_max": 60,
  "applied": 9,
  "pending": [],
  "pending_por_risco": {"critica": 0, "melhoria": 0, "rotina": 0, "n/c": 0},
  "atualizado": true
}
```

### Aplicação automática no deploy + on-demand (Painel "Atualizações")

No deploy, após subir os containers, o pipeline roda:

```bash
docker compose exec -T backend python -m catalog_server.versioning apply --origem deploy
```

Isso **aplica todas as migrações pendentes automaticamente** e registra o evento
na tabela `sistema_atualizacoes` (ver migração `0061`), alimentando o histórico
do painel. Portal do fornecedor (`/api/fornecedor/...`) e demais rotas continuam
fora desse fluxo.

**Quem aplica migrações (e onde):**

- **Produção**: somente o passo explícito do pipeline. O container roda com
  `AUTO_MIGRATE=0` — o processo web nunca executa DDL, então uma migração
  problemática falha no deploy (visível no log do Actions) em vez de derrubar
  o app em crash-loop.
- **Dev/local**: o auto-apply no primeiro acesso ao banco permanece ligado
  (default `AUTO_MIGRATE=1`) por conveniência.
- O runner usa um **advisory lock** do Postgres (`pg_advisory_lock`), então
  execuções concorrentes (deploy + painel, ou dois processos subindo juntos)
  são serializadas com segurança.

O frontend (menu **Admin → Atualizações**) também permite aplicar migrações
pendentes **sob demanda** (útil para hotfix sem redeploy completo), via
`POST /api/sistema/updates/apply`:

```json
{ "risco": "critica" | "rotina" | "melhoria" | "todos" }
```

- `critica` → aplica apenas migrações `critica`.
- `rotina` → aplica `critica` + `rotina`.
- `melhoria` → aplica tudo (`critica` + `rotina` + `melhoria`).
- `todos` → aplica todas as pendentes.

Críticas sempre entram antes (não é possível pular a ordem de migração). O
endpoint devolve o `system_status()` atualizado (`ok`, `nivel`, `pending`, …).
Em caso de falha devolve `{ "ok": false, "error": "..." }` com HTTP 500.

O painel também expõe `GET /api/sistema/updates/log` com o **Histórico** de
atualizações (versão, nível/risco, schema antes/depois, origem deploy/painel,
usuário e erro).

### Processo de publicação e versionamento

Versionamento semântico `MAJOR.MINOR.PATCH`:

- **PATCH** (`vX.Y.Z+1`) → correção (bugfix).
- **MINOR** (`vX.Y+1.0`) → melhoria / novo recurso (não-breaking).
- **MAJOR** (`vX+1.0.0`) → mudança breaking (contrato/schema incompatível).

#### Manifesto de release (`releases/vX.Y.Z.json`)

Cada conjunto de mudanças vem com um manifesto commitado junto ao código:

```json
{
  "versao": "v1.5.0",
  "componentes": ["backend", "frontend", "schema"],
  "correcoes": ["O que foi corrigido"],
  "melhorias": ["O que foi melhorado"],
  "recursos": ["O que foi adicionado"]
}
```

Ele alimenta o **Histórico** do painel (o que mudou, por release) e a seção
**"Rascunhos pendentes"** — releases implementadas em dev que ainda não foram
publicadas (`GET /api/sistema/releases/pendentes`). Um manifesto só é marcado
como publicado quando o deploy o registra no log.

**Toda publicação gera registro**, independente do componente: o passo final do
workflow (`versioning publicar --componentes ...`) fecha os manifestos cujos
componentes declarados estão contidos no escopo publicado. Regra do subconjunto:
um manifesto `[backend, frontend]` publicado por partes não fecha — publique com
escopo igual ao declarado ou com `todos`.

#### Documentação obrigatória de migração (`MUDANCA`)

Qualquer **mudança no banco de dados** vem documentada dentro da própria
migração:

```python
VERSION = 63
RISCO = "rotina"
NAME = "exemplo"

MUDANCA = {
    "o_que":     ["Adiciona coluna X na tabela Y"],   # obrigatório
    "porque":    ["Suporta o fluxo Z do módulo W"],   # obrigatório
    "novidades": ["O que entra de novo, e por quê"],  # opcional
}
```

- O runner **bloqueia** o apply de migração nova sem `MUDANCA` (válvula de
  emergência: `apply --sem-docs`).
- A documentação aparece **antes** do deploy (seção "Migrações pendentes" do
  painel) e **depois** de aplicar (linhas expansíveis no Histórico).

#### Publicar (autorização explícita)

A publicação nunca é automática. A tela de produção não possui campos: a RC é
resolvida automaticamente e versão/componentes são lidos do manifesto versionado.
O pipeline aplica internamente o seguinte mapeamento:

| Componente | Promove backend | Promove frontend | Migrações |
|---|---|---|---|
| manifesto com `deployment` | ✅ | ✅ | ✅ |
| `backend` | ✅ | — | ✅ |
| `schema` | ✅ (as migrações vivem na imagem) | — | ✅ |
| `frontend` | — | ✅ | — |

Ou seja: correção interna de backend ou migração **não derruba o frontend**;
recurso visual novo publica **só o frontend**. Regra de ouro: se a mudança
altera **assinatura de API**, o manifesto deve listar `backend + frontend`
(publicar juntos).

Fluxo completo:
1. Implemente em dev; commit com código, migration `00XX_*.py` (com `RISCO`)
   e o manifesto `releases/vX.Y.Z.json`.
2. Execute staging completo escolhendo o incremento SemVer.
3. Autorize produção com um segundo clique; o pipeline seleciona a candidata e
   registra somente o manifesto da versão promovida.
4. Confira no painel **Admin → Atualizações**: versão, estado e notas.

> Tags são evidências imutáveis, não gatilhos automáticos. A candidata nasce
> depois do staging verde e a definitiva nasce depois da produção verde.

### Indisponibilidade e modo manutenção

Comportamento previsto quando um serviço fica fora do ar:

| Cenário | O que acontece |
|---|---|
| Backend reiniciando (deploy/restart) | nginx devolve 502/503 → SPA entra em **modo manutenção** (overlay "Sistema em manutenção") |
| Banco fora do ar / em manutenção | Endpoints respondem `503 {"code":"db_indisponivel"}` (`/api/pronto` também 503) → mesmo overlay |
| Usuário abre o sistema com backend fora | Vê o overlay de manutenção **em vez da tela de login** |
| Serviço volta | Overlay detecta sozinho (polling `GET /api/pronto` a cada 10s), recarrega a aplicação e some |

- `/api/health` = *liveness* do container (não olha o banco, não causa loop de
  restart). `/api/pronto` = *readiness* real (executa `SELECT 1`).
- Conexões com o banco usam `connect_timeout=3s`: falham rápido com 503 em vez
  de pendurar o worker. Não há pool persistente — quando o banco volta, o
  backend se recupera sozinho, sem restart.
- No deploy **com migrações**, o pipeline para o backend antes do DDL
  (`docker compose stop backend`) e aplica as migrações num container one-off
  com a imagem nova — usuários veem o banner de manutenção nessa janela.
  Deploy só-frontend não toca no backend.

### Autenticação por token (API)

Toda rota `/api/*` (exceto `health`, `login`, `logout`, `primeiro-usuario` e
`POST /api/usuarios` para o primeiro admin, mais o portal do fornecedor) exige
`Authorization: Bearer <token>`. O token é emitido no `/api/login` (HMAC
assinado com `CATALOG_SECRET`, TTL 7 dias) e enviado pelo frontend em todas as
chamadas. Em `401` o frontend limpa o token e volta ao login.

> O backend **não** expõe a porta `8000` no host — só na rede Docker. O acesso
> externo entra via proxy (`:80`/`:6173`), que faz o proxy de `/api`. App e
> Portal do Fornecedor ficam protegidos pelo token; o proxy deve continuar
> restrito por rede conforme necessário.

## Ambiente local (espelha a produção)

O `docker-compose.yml` local tem a MESMA topologia do `docker-compose.prod.yml`:

```
navegador → nginx (:8080) ─┬─ /api,/images,/compras/pedidos,/orcamentos,/fornecedor → backend:8000
                           └─ / (SPA em dev) → vite:5173 (HMR atrás do proxy)
backend → apenas rede interna · APP_VERSION=dev · AUTO_MIGRATE=0
db      → postgres (dados no volume postgres-data)
```

- As rotas de backend vivem em **um único arquivo** (`frontend/nginx.backend-routes.conf`)
  incluído pelo nginx de dev (`nginx.dev.conf`) e pelo de produção (`nginx.conf`) —
  rota nova do Flask entra lá e vale nos dois ambientes.
- Migrações NÃO aplicam sozinhas no local (paridade com produção). Após criar/
  alterar migração: `docker compose exec -T backend python -m catalog_server.versioning apply --origem local`
- O serviço `vite` roda com `CHOKIDAR_USEPOLLING=true`: eventos de alteração de
  arquivo não cruzam o bind mount Windows→Docker, e sem polling o Vite serve a
  versão em cache (HMR/F5 não refletem edições).
- Subir: `docker compose up -d` → sistema em `http://localhost:8080`.

### Política de cache do frontend (produção)

- `/assets/*` — arquivos com hash no nome: `Cache-Control: public, immutable`
  (1 ano). Conteúdo novo recebe nome novo, então é seguro.
- `location /` (index.html **e qualquer fallback da SPA**) →
  `Cache-Control: no-cache`: o navegador revalida a cada acesso. Garante que um
  deploy novo apareça sem hard-refresh.

> Histórico: até a v1.6.3 o fallback respondia `immutable` por 1 ano; URLs de
> impressão abertas nesse período ficaram "envenenadas" no navegador do usuário
> (serviam a SPA/login mesmo com o servidor correto). Procedimento para URL
> afetada: **Ctrl+F5** na aba (hard reload ignora immutable) — uma única vez.

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
