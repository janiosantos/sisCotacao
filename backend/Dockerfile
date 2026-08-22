FROM python:3.14-slim
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
WORKDIR /app
# Contexto de build = raiz do repositório (ver docker-compose*.yml)
COPY backend/catalog_server/ catalog_server/
COPY backend/migrations/ migrations/
# Contrato OpenAPI (servido em /api/openapi.json)
COPY backend/openapi.json openapi.json
# Suíte de testes (CI roda pytest dentro de container efêmero da imagem)
COPY backend/tests/ tests/
# Scraper legado (importado por classification/parse_url; execução futura via task)
COPY app/ app/
# Manifestos de release (lidos pelo versioning ao publicar)
COPY releases/ releases/
RUN pip install --no-cache-dir flask python-dotenv requests beautifulsoup4 lxml colorlog fake-useragent sqlalchemy "psycopg[binary]"
EXPOSE 8000
CMD ["python", "-m", "catalog_server.run_server", "--port", "8000", "--host", "0.0.0.0"]
