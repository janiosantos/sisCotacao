"""Processo dedicado para a fila de impressao ESC/POS."""
from __future__ import annotations

import signal

from catalog_server.services.impressao import impressao_service


def main() -> None:
    def _encerrar(*_args) -> None:
        impressao_service.stop_worker()

    signal.signal(signal.SIGTERM, _encerrar)
    signal.signal(signal.SIGINT, _encerrar)
    print("impressao-worker: aguardando trabalhos")
    impressao_service.run_worker()


if __name__ == "__main__":
    main()
