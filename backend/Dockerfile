FROM python:3.14-slim
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
ENV TZ=America/Sao_Paulo
WORKDIR /app
COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*
# Contexto de build = raiz do repositório (ver docker-compose*.yml)
COPY backend/catalog_server/ catalog_server/
COPY backend/migrations/ migrations/
# Contrato OpenAPI (servido em /api/openapi.json)
COPY backend/openapi.json openapi.json
# Suíte de testes (CI roda pytest dentro de container efêmero da imagem).
# Mantém a estrutura do repositório para o conftest e o testpaths do projeto.
COPY backend/tests/ backend/tests/
# Scraper legado (importado por classification/parse_url; execução futura via task)
COPY app/ app/
# Manifestos de release (lidos pelo versioning ao publicar)
COPY releases/ releases/
# Scripts operacionais (inclui o backup validado pela suíte backend)
COPY scripts/ scripts/
ARG INSTALL_TEST_DEPS=0
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --no-install-project && \
    if [ "$INSTALL_TEST_DEPS" = "1" ]; then uv sync --frozen --no-install-project; fi
EXPOSE 8000
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "4", \
     "--timeout", "60", "--graceful-timeout", "30", "catalog_server.run_server:app"]
