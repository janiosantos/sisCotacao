"""Worker RQ — processa a fila 'default' (rechecagem, outbox futuro)."""
from __future__ import annotations

import os

from redis import Redis
from rq import Worker

from catalog_server.jobs import _redis


def main() -> None:
    queues = [q.strip() for q in os.getenv("RQ_QUEUES", "default").split(",") if q.strip()]
    Worker(queues, connection=_redis()).work(with_scheduler=True)


if __name__ == "__main__":
    main()