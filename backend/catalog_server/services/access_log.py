"""Filtros pequenos para reduzir ruido operacional sem ocultar falhas."""
from __future__ import annotations

import logging
import re
from urllib.parse import urlsplit


_PROBE_PATHS = frozenset({"/api/health", "/api/pronto"})


def _request_line(record: logging.LogRecord) -> str:
    requestline = getattr(record, "requestline", "")
    if requestline:
        return str(requestline)
    args = getattr(record, "args", ())
    if isinstance(args, tuple):
        for value in args:
            candidate = str(value or "")
            if re.match(r"^(GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS)\s+\S+\s+HTTP/", candidate):
                return candidate
    try:
        match = re.search(r'"((?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS)\s+\S+\s+HTTP/[^" ]+)"', record.getMessage())
    except Exception:
        match = None
    if match:
        return match.group(1)
    return ""


class HealthProbeAccessFilter(logging.Filter):
    """Oculta somente as linhas de acesso dos probes conhecidos."""

    def filter(self, record: logging.LogRecord) -> bool:
        line = _request_line(record)
        if not line:
            return True
        parts = line.split()
        if len(parts) < 2:
            return True
        try:
            path = urlsplit(parts[1]).path
        except ValueError:
            return True
        return path not in _PROBE_PATHS


def configure_health_probe_logging() -> None:
    """Registra o filtro uma vez nos access loggers usados localmente e em WSGI."""
    for logger_name in ("werkzeug", "gunicorn.access"):
        logger = logging.getLogger(logger_name)
        if not any(isinstance(item, HealthProbeAccessFilter) for item in logger.filters):
            logger.addFilter(HealthProbeAccessFilter())
