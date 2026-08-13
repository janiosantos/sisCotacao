#!/usr/bin/env python3
"""Envia um cupom ESC/POS de teste direto à impressora térmica em rede.

Útil para validar o emulador (printer_emulator) sem depender do backend:
    python send_test.py --host 127.0.0.1 --port 9100

A sequência de comandos é a mesma gerada por catalog_server/services/impressao.py.
"""
from __future__ import annotations

import argparse
import socket

INIT = b"\x1b\x40"
ALIGN_CENTER = b"\x1b\x61\x01"
ALIGN_LEFT = b"\x1b\x61\x00"
FONT_BIG = b"\x1b\x21\x30"
FONT_NORMAL = b"\x1b\x21\x00"
REVERSE_ON = b"\x1b\x42\x01"
REVERSE_OFF = b"\x1b\x42\x00"
FEED3 = b"\x1b\x64\x03"
CUT = b"\x1d\x56\x42\x00"

COLS = 42


def enc(texto: str) -> bytes:
    return str(texto).encode("cp850", "replace")


def linha(esq: str, dir_: str) -> bytes:
    esp = max(1, COLS - len(esq) - len(dir_))
    return enc(esq + " " * esp + dir_ + "\n")


def separador(caractere: str = "=") -> bytes:
    return enc(caractere * COLS + "\n")


def cupom_teste() -> bytes:
    out = bytearray()
    out += INIT
    out += ALIGN_CENTER + FONT_BIG + enc("COTAÇÕES\n")
    out += FONT_NORMAL + enc("ORÇAMENTO TESTE\n")
    out += ALIGN_LEFT
    out += separador()
    out += enc("Cliente: Emulador de impressora\n")
    out += enc("Data: teste\n")
    out += separador("-")
    out += linha("1x Produto Exemplo", "R$ 12.50")
    out += separador("-")
    out += linha("Subtotal", "R$ 12.50")
    out += linha("Desconto", "R$ 0.00")
    out += REVERSE_ON + linha("TOTAL", "R$ 12.50") + REVERSE_OFF
    out += FEED3
    out += CUT
    return bytes(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="IP da impressora/emulador")
    parser.add_argument("--port", type=int, default=9100, help="Porta JetDirect")
    args = parser.parse_args()

    dados = cupom_teste()
    print(f"Enviando {len(dados)} bytes ESC/POS para {args.host}:{args.port} ...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(6)
        s.connect((args.host, args.port))
        s.sendall(dados)
    print("OK. Confira o recibo em http://localhost:8081")


if __name__ == "__main__":
    main()
