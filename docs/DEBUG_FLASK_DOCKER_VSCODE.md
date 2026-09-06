# Depurar o Flask no Docker com VS Code

Esta configuracao e exclusiva do ambiente local. O backend de staging e
producao continua usando Gunicorn e nao instala nem expoe o `debugpy`.

## Iniciar

1. Abra o projeto inteiro no VS Code e aceite as extensoes Python recomendadas.
2. Coloque um breakpoint em um arquivo dentro de `backend/catalog_server/`.
3. Abra **Executar e Depurar** (`Ctrl+Shift+D`).
4. Selecione **Docker: Flask (debugpy)** e pressione `F5`.
5. A tarefa prepara o container, publica `127.0.0.1:5678` e o VS Code conecta.
6. Acesse normalmente `http://localhost:8080` e execute a acao que passa pela
   linha marcada.

Na primeira execucao, o build instala a dependencia de desenvolvimento. Nas
seguintes, as camadas Docker permanecem em cache. O `--wait-for-client` impede
que a aplicacao execute antes de o depurador conectar, permitindo breakpoints
inclusive durante a criacao do Flask.

## Mapeamento e seguranca

- Codigo no computador: `${workspaceFolder}/backend`.
- Codigo no container: `/app`.
- Porta de depuracao: `5678`, vinculada somente a `127.0.0.1`.
- Apenas um processo Flask e iniciado, sem reloader e sem workers Gunicorn.
- Banco e demais servicos Docker continuam os mesmos do DEV local.

## Restaurar o servidor normal

Ao terminar, execute no VS Code **Terminal > Executar Tarefa > Docker: restaurar
backend Gunicorn**. O comando recria somente o backend DEV com a configuracao
normal de `docker-compose.yml`; nao executa migrations e nao toca em staging ou
producao.

## Diagnostico rapido

Se o breakpoint ficar cinza, confira se o VS Code abriu a raiz do projeto e se
o arquivo esta dentro de `backend/`. Para conferir o listener:

```powershell
docker compose -f docker-compose.yml -f docker-compose.debug.yml logs backend
Test-NetConnection 127.0.0.1 -Port 5678
```

Se a porta estiver ocupada, encerre o processo local que a utiliza ou altere a
porta nos dois arquivos: `docker-compose.debug.yml` e `.vscode/launch.json`.
