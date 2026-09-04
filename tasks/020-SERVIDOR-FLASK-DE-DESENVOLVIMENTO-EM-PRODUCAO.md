# PROBLEM

- **Severidade:** alta
- **Categoria:** ponto fraco
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/Dockerfile:1-27`; `backend/catalog_server/run_server.py:10-24`; `deployment/compose/docker-compose.prod.yml:17-54`; `backend/catalog_server/app_factory.py:530`

## Explicação para leigos

O backend de produção é iniciado com o servidor embutido do Flask, criado para desenvolvimento. Ele oferece menos isolamento, controle de processos e recuperação sob carga do que um servidor de aplicação próprio para produção.

## Evidência e análise técnica

O `CMD` da imagem executa `catalog_server.run_server`, que chama `app.run(...)`. O serviço `backend` do compose de produção não substitui esse comando. Não há Gunicorn, Waitress ou outro servidor WSGI nas dependências da imagem.

Esse desenho mantém um único processo de aplicação e torna reinício gracioso, limite de workers, timeout e reciclagem de processos dependentes do servidor de desenvolvimento. Há ainda um cuidado adicional: `create_app()` inicia um worker de impressão em thread; simplesmente adicionar vários workers WSGI criaria várias threads concorrentes de impressão.

## Impacto

Uma requisição lenta, vazamento de memória ou falha do processo pode reduzir a capacidade ou interromper todo o ERP. A evolução para mais concorrência pode duplicar processamento da fila de impressão se a thread não for separada antes.

## Solução proposta

Executar o Flask sob Gunicorn com configuração explícita de workers, threads, timeout, graceful timeout e logs. Mover a impressão para processo/fila dedicada com claim transacional, antes de habilitar múltiplos workers web. Fixar a nova dependência no lock e validar SIGTERM, health check, uploads e requisições longas.

Realizar posteriormente teste de concorrência e desligamento gracioso em staging. Nenhum servidor foi iniciado nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/Dockerfile b/backend/Dockerfile
@@
-CMD ["python", "-m", "catalog_server.run_server", "--port", "8000", "--host", "0.0.0.0"]
+CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "4", \
+     "--timeout", "60", "--graceful-timeout", "30", "catalog_server.run_server:app"]
diff --git a/backend/catalog_server/app_factory.py b/backend/catalog_server/app_factory.py
@@
-    impressao_service.start_worker()
+    # Impressão executada por serviço dedicado, não por cada worker web.
```
