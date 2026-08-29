# Ativação do HTTPS (Let's Encrypt) em Produção

> Cenário: domínio `siscom.casalm.com.br`, **atrás de CGNAT** (portas 80/443 não
> são abertas para a internet). Usamos **DNS-01 via Cloudflare** — o certificado
> é emitido criando/removendo um registro TXT de validação por API, sem precisar
> de porta aberta. A renovação é automática (loop no container `certbot`).

## Pré-requisitos

1. **Token de API do Cloudflare** com permissão **Zone → DNS → Edit** (escopo:
   domínio `casalm.com.br`).
2. **Redirecionamento de porta** no roteador/CGNAT: a porta pública que você usa
   hoje (ex.: **6173**) deve apontar para a **porta interna 443** do servidor.
   (Hoje aponta para a 80; com TLS, precisa apontar para a 443.)
   - Se a porta pública 80 também estiver roteada, o nginx responde o redirect
     http → https.

## Passos (no servidor de produção)

```bash
cd ~/Projetos/ecommerce_scraper   # ou o path real do deploy

# 1) Credenciais do Cloudflare — FORA do workspace do runner (o checkout do
#    deploy limpa arquivos não versionados). O compose monta esse diretório.
mkdir -p /home/jpsantos/siscom/certbot
# (se você criou cloudflare.ini no workspace, mova-o:)
#   mv deployment/certbot/cloudflare.ini /home/jpsantos/siscom/certbot/
cp deployment/certbot/cloudflare.ini.example /home/jpsantos/siscom/certbot/cloudflare.ini
nano /home/jpsantos/siscom/certbot/cloudflare.ini   # cole o token
chmod 600 /home/jpsantos/siscom/certbot/cloudflare.ini

# 2) Sobe a stack (certbot emite o certificado na 1ª subida; o nginx aguarda
#    e troca para TLS assim que o cert aparece)
docker compose -f deployment/compose/docker-compose.prod.yml up -d --build

# 3) Acompanhe a emissão (DNS-01 leva ~1-2 min)
docker compose -f deployment/compose/docker-compose.prod.yml logs -f certbot

# 4) Confirme o certificado
docker compose -f deployment/compose/docker-compose.prod.yml exec certbot certbot certificates
```

## Resultado

- `https://siscom.casalm.com.br:6173` servindo a aplicação com certificado
  Let's Encrypt válido.
- `http://...` (porta 80, se roteada) redireciona para `https://...`.
- **Renovação automática**: o container `certbot` roda `certbot renew` a cada
  12h; o nginx recarrega a configuração quando o certificado é renovado
  (mtime muda) — sem intervenção manual.
- Links de convite ao fornecedor (WhatsApp/e-mail) passam a ser gerados como
  `https://...` automaticamente (nginx envia `X-Forwarded-Proto` ao backend).

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| `certbot` falha na emissão | Token inválido/sem permissão | Confira o token e o escopo Zone:DNS:Edit |
| `certbot` aguardando credencial | `/home/jpsantos/siscom/certbot/cloudflare.ini` não existe | Crie o arquivo (chmod 600) — o certbot emite no próximo loop |
| `certbot: error: unrecognized arguments: --dns-cloudflare` | Plugin ausente na imagem | Use `certbot/dns-cloudflare` no lugar de `certbot/certbot` no compose |
| Site continua em HTTP após emissão | nginx ainda não recarregou | `docker compose -f ... restart frontend` (ou aguarde ~60s — o entrypoint troca para TLS) |
| Porta pública errada | Roteador apontando 80 em vez de 443 | Ajuste o redirecionamento p/ porta interna 443 |

## Fallback HTTP (sem certificado)

Sem o certificado, o nginx usa `nginx.http.conf` (HTTP na porta 80) — o staging
e o 1º boot de produção continuam funcionando normalmente até o cert existir.