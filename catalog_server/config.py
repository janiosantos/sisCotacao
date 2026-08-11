from __future__ import annotations

import os
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent

PROJECT_DIR = MODULE_DIR.parent

CATALOG_DB = PROJECT_DIR / "database" / "crawler.db"

SYSTEM_DB = Path(os.getenv("SYSTEM_DB", str(MODULE_DIR / "data" / "server.db")))

# Cache de páginas-fonte (HTML) em banco separado, para manter o banco de
# dados principal enxuto e rápido (evita que os blobs de HTML inflem o DB).
CACHE_DB = Path(os.getenv("CACHE_DB", str(MODULE_DIR / "data" / "server_cache.db")))

IMAGES_DIR = Path(os.getenv("IMAGES_DIR", str(PROJECT_DIR / "images")))

HOST = os.getenv("CATALOG_HOST", "0.0.0.0")

PORT = int(os.getenv("CATALOG_PORT", "8000"))

DEBUG = os.getenv("CATALOG_DEBUG", "0") == "1"

OPEN_BROWSER = os.getenv("CATALOG_OPEN_BROWSER", "1") == "1"

SECRET_KEY = os.getenv("CATALOG_SECRET", "catalog-server-local-dev")

PAGE_SIZE = 60

COTACAO_STATUSES = ["aberta", "fechada", "cancelada", "pendente", "analise", "finalizada"]

FORNECEDOR_STATUS = ["pendente", "respondido"]

# Microserviço "Cotações IA Importer" (recebe textos/PDF/WhatsApp e devolve
# produtos do catálogo via busca semântica no Qdrant).
IA_URL = os.getenv("IA_URL", "http://127.0.0.1:8001").rstrip("/")

IA_TIMEOUT = int(os.getenv("IA_TIMEOUT", "240"))

# Limite do catálogo enviado no seed (variantes reais do crawler.db).
IA_SEED_LIMIT = int(os.getenv("IA_SEED_LIMIT", "2000"))
