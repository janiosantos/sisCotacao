from __future__ import annotations

import argparse
import threading
import webbrowser

from catalog_server import config
from catalog_server.app_factory import create_app

app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor local do catálogo e cotações")
    parser.add_argument("--host", default=config.HOST)
    parser.add_argument("--port", type=int, default=config.PORT)
    args = parser.parse_args()

    if config.OPEN_BROWSER and args.host in ("0.0.0.0", "127.0.0.1", "localhost"):
        threading.Timer(1.0, webbrowser.open, args=(f"http://127.0.0.1:{args.port}",)).start()

    print(f"Sistema de cotações rodando em http://{args.host}:{args.port}")
    print("Acesse de outros computadores da rede usando o IP desta máquina.")
    app.run(host=args.host, port=args.port, debug=config.DEBUG)


if __name__ == "__main__":
    main()
