# PROBLEM

- **Severidade:** alta
- **Categoria:** ponto fraco
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/db.py:45-66`; `backend/catalog_server/pgsql.py:292-324, 340-341`

## Explicação para leigos

Cada acesso ao banco monta uma estrutura nova de conexão e a destrói logo depois. O sistema paga repetidamente o custo de abrir conexão com o PostgreSQL em vez de reutilizar conexões prontas.

## Evidência e análise técnica

Cada `system_conn()` chama `connect(DATABASE_URL)`. O construtor de `PgConnection` executa `sqlalchemy.create_engine(...)` e obtém uma conexão raw. No fechamento, chama `self._engine.dispose()`. Como o `Engine` e seu pool nascem e morrem em cada unidade de trabalho, `pool_pre_ping=True` não oferece pooling entre requisições.

O padrão aparece em centenas de operações e algumas requisições abrem várias `system_conn()` sequenciais. Sob carga, isso aumenta handshakes, latência e pressão em `max_connections`.

## Impacto

Listagens, PDV e relatórios ficam mais lentos conforme o número de operadores cresce. Picos podem esgotar conexões do PostgreSQL ou CPU, especialmente após adoção de múltiplos workers web.

## Solução proposta

Manter um `Engine` por URL/processo, com `QueuePool` dimensionado e limites explícitos (`pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`). `PgConnection.close()` deve devolver a conexão ao pool, não descartar o engine. O engine deve ser descartado somente no encerramento do processo.

Medir posteriormente latência e conexões abertas com carga concorrente, além de testar reconexão após reinício do banco. Nenhum benchmark foi executado agora.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/pgsql.py b/backend/catalog_server/pgsql.py
@@
+_ENGINES: dict[str, sqlalchemy.Engine] = {}
+
+def _engine(url: str):
+    return _ENGINES.setdefault(url, sqlalchemy.create_engine(
+        url, pool_pre_ping=True, pool_size=10, max_overflow=20,
+        pool_timeout=10, pool_recycle=1800,
+        connect_args={"connect_timeout": 3},
+    ))
@@
-        self._engine = sqlalchemy.create_engine(url, ...)
+        self._engine = _engine(url)
@@
-        finally:
-            self._engine.dispose()
+        # raw_connection.close() devolve a conexão ao pool compartilhado.
```
