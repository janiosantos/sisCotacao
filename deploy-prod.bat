@echo off
setlocal
rem ============================================================
rem Deploy PROD (Modelo B): build local + save + scp + load
rem Ajuste as variaveis REMOTE, REMOTE_DIR e IMG_DIR conforme o
rem seu servidor.
rem ============================================================

set REMOTE=root@10.189.14.8
set REMOTE_DIR=/home/jpsantos/siscom
set TAR=%~dp0deploy-images.tar

echo.
echo === 1/4 Build local das imagens ===
docker compose -f docker-compose.prod.yml build
if errorlevel 1 goto :erro

echo.
echo === 2/4 Salvando imagens em %TAR% ===
docker save -o "%TAR%" siscom-backend:latest siscom-frontend:latest
if errorlevel 1 goto :erro

echo.
echo === 3/4 Enviando imagens e compose para %REMOTE% ===
scp docker-compose.prod.yml %REMOTE%:%REMOTE_DIR%/
if errorlevel 1 goto :erro
scp "%TAR%" %REMOTE%:%REMOTE_DIR%/deploy-images.tar
if errorlevel 1 goto :erro

echo.
echo === 4/4 Carregando imagens e reiniciando no servidor ===
ssh %REMOTE% "cd %REMOTE_DIR% && docker load -i deploy-images.tar && docker compose -f docker-compose.prod.yml up -d"
if errorlevel 1 goto :erro

echo.
echo === Deploy concluido ===
echo Frontend: http://%REMOTE:*@=%
echo Backend:  http://%REMOTE:*@=:8000
del "%TAR%"
goto :fim

:erro
echo.
echo FALHA no deploy.
del "%TAR%" 2>nul
exit /b 1

:fim
endlocal