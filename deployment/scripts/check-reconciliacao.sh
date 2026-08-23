#!/usr/bin/env bash
# Gate de reconciliação de estoque (ADR 0003): saldos divergentes dos
# movimentos falham o deploy de staging.
set -euo pipefail

docker compose exec -T backend python -c "
import sys
sys.path.insert(0, '/app')
from catalog_server.repositories import estoque_repo
div = estoque_repo.reconciliar_tudo()
if div:
    print('DIVERGENCIAS:', len(div))
    for d in div[:10]:
        print(d)
    sys.exit(1)
print('estoque reconciliado OK')
"
