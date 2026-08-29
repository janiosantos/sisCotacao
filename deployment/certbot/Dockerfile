# Imagem do certbot com o plugin DNS-01 do Cloudflare (desafio sem abrir portas
# — necessário por estar atrás de CGNAT). A imagem oficial certbot/certbot NÃO
# inclui o plugin; instalamos aqui no build.
FROM certbot/certbot:latest

RUN pip install --no-cache-dir certbot-dns-cloudflare