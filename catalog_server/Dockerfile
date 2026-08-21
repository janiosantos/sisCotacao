FROM python:3.14-slim
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
WORKDIR /app
COPY catalog_server/ catalog_server/
COPY app/ app/
COPY scripts/ scripts/
RUN pip install --no-cache-dir flask python-dotenv requests beautifulsoup4 lxml colorlog fake-useragent sqlalchemy "psycopg[binary]"
EXPOSE 8000
CMD ["python", "-m", "catalog_server.run_server", "--port", "8000", "--host", "0.0.0.0"]
