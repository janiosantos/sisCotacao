@echo off
setlocal
rem ============================================================
rem Deploy dos DADOS do banco (dev local -> servidor prod)
rem Faz pg_dump data-only do banco local e restaura no servidor.
rem O SCHEMA nao vem: as migracoes ja rodam no backend ao subir.
rem ============================================================

set REMOTE=root@10.189.14.8
set REMOTE_DIR=/home/jpsantos/siscom
set LOCAL_DB=ecommerce_scraper-db-1
set REMOTE_DB=siscom-db-1
set DUMP=%~dp0catalog-data.dump

echo.
echo === 1/4 Dump dos dados no banco local (%LOCAL_DB%) ===
docker exec %LOCAL_DB% pg_dump -U catalog -d catalog --data-only --no-owner --no-privileges --exclude-table=schema_migrations -f /tmp/catalog-data.dump
if errorlevel 1 goto :erro
docker cp %LOCAL_DB%:/tmp/catalog-data.dump "%DUMP%"
if errorlevel 1 goto :erro

echo.
echo === 2/4 Enviando dump para %REMOTE% ===
scp "%DUMP%" %REMOTE%:%REMOTE_DIR%/catalog-data.dump
if errorlevel 1 goto :erro
scp "%~dp0deploy\truncate_data.sql" "%~dp0deploy\reset_sequences.sql" %REMOTE%:%REMOTE_DIR%/
if errorlevel 1 goto :erro

echo.
echo === 3/4 Truncando dados existentes e restaurando (%REMOTE_DB%) ===
ssh %REMOTE% "docker cp %REMOTE_DIR%/truncate_data.sql %REMOTE_DB%:/tmp/truncate_data.sql && docker cp %REMOTE_DIR%/catalog-data.dump %REMOTE_DB%:/tmp/catalog-data.dump && docker exec %REMOTE_DB% psql -U catalog -d catalog -v ON_ERROR_STOP=1 -f /tmp/truncate_data.sql && docker exec %REMOTE_DB% psql -U catalog -d catalog -v ON_ERROR_STOP=1 -f /tmp/catalog-data.dump"
if errorlevel 1 goto :erro

echo.
echo === 4/4 Recalculando sequencias ===
ssh %REMOTE% "docker cp %REMOTE_DIR%/reset_sequences.sql %REMOTE_DB%:/tmp/reset_sequences.sql && docker exec %REMOTE_DB% psql -U catalog -d catalog -v ON_ERROR_STOP=1 -f /tmp/reset_sequences.sql"
if errorlevel 1 goto :erro

echo.
echo === Dados restaurados com sucesso ===
del "%DUMP%"
goto :fim

:erro
echo.
echo FALHA ao restaurar dados.
del "%DUMP%" 2>nul
exit /b 1

:fim
endlocal