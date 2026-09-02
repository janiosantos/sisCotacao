import logging

from catalog_server.services.access_log import HealthProbeAccessFilter


def _record(requestline: str) -> logging.LogRecord:
    record = logging.LogRecord("werkzeug", logging.INFO, __file__, 1, '"%s" 200 -', (requestline,), None)
    record.requestline = requestline
    return record


def test_health_probes_nao_poluem_access_log():
    filtro = HealthProbeAccessFilter()
    assert filtro.filter(_record("GET /api/health HTTP/1.1")) is False
    assert filtro.filter(_record("GET /api/pronto?check=1 HTTP/1.0")) is False


def test_filtro_nao_oculta_rotas_normais_nem_erros_sem_requestline():
    filtro = HealthProbeAccessFilter()
    assert filtro.filter(_record("GET /api/clientes HTTP/1.1")) is True
    assert filtro.filter(logging.LogRecord("werkzeug", logging.ERROR, __file__, 1, "falha", (), None)) is True
