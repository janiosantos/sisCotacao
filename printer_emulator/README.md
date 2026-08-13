# Emulador de impressora térmica (ESC/POS)

Simula uma impressora térmica de rede para desenvolvimento. Baseado no
[gilbertfl/escpos-netprinter](https://github.com/gilbertfl/escpos-netprinter):
o container escuta comandos ESC/POS via JetDirect (9100) e LPD (515) e
"imprime" o recibo como página HTML acessível no navegador — no lugar de papel.

## Subir o emulador

```powershell
cd printer_emulator
docker compose up -d
```

| Serviço | Porta host | Uso                                              |
| ------- | ---------- | ------------------------------------------------ |
| JetDirect (RAW ESC/POS) | `9100` | porta padrão de impressão do backend |
| LPD | `515` | impressão via LPD |
| Web (recibos) | `8081` | confira o recibo impresso |
| CUPS admin | `631` | interface administrativa (opcional) |

Os recibos ficam no volume `escpos-receipts` (`/home/escpos-emu/web`).

## Testar o emulador sozinho

```powershell
python printer_emulator/send_test.py --host 127.0.0.1 --port 9100
```

Depois abra `http://localhost:8081` e veja o cupom renderizado.

## Monitor da impressora (página dedicada)

Abra `http://localhost:8081/static/monitor.html`. A página lê a fila a cada 2s
e exibe automaticamente o **último recibo impresso** — sem refresh manual, ideal
para deixar aberta ao lado do PDV.

As demais telas também atualizam sozinhas:
- `/recus` — a lista recarrega quando chega um recibo novo.
- `/recus/<id>` — redireciona para o recibo mais recente.

## Integrar ao backend (PDV)

O PDV já envia o cupom ESC/POS direto ao host/porta gravados em
`impressao_config` (F7 no PDV → *Retaguarda de impressão*):

1. Suba o emulador (comando acima).
2. No PDV pressione **F7** e configure:
   - **Host**: `host.docker.internal` (backend rodando em container Docker Desktop)
   - **Porta**: `9100`
   - **Papel (mm)**: `80` (ou `58`)
3. Clique em **Testar** — o cupom de teste aparece em `http://localhost:8081`.

> Se o backend rodar direto no host (sem Docker), use `host` `127.0.0.1`.
> O `host.docker.internal` só funciona em Docker Desktop (Windows/Mac).

## Comandos úteis

```powershell
docker compose logs -f escpos          # logs do emulador
docker compose down                    # para e remove o container
docker compose down -v                 # para e apaga os recibos (volume)
```
