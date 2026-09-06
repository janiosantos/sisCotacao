# Depurar o Flask no Docker com VS Code

Esta configuracao e exclusiva do ambiente local. O backend de staging e
producao continua usando Gunicorn e nao instala nem expoe o `debugpy`.

## Iniciar

1. Abra o projeto inteiro no VS Code e aceite as extensoes Python recomendadas.
2. Coloque um breakpoint em um arquivo dentro de `backend/catalog_server/`.
3. Abra **Executar e Depurar** (`Ctrl+Shift+D`).
4. Selecione **Docker: Flask (debugpy)** e pressione `F5`.
5. A tarefa prepara o container, espera o `debugpy` abrir `127.0.0.1:5678` e
   so entao o VS Code conecta.
6. Acesse normalmente `http://localhost:8080` e execute a acao que passa pela
   linha marcada.
7. Ao encerrar a sessao de depuracao, o VS Code restaura automaticamente o
   backend normal em Gunicorn.

Na primeira execucao, o build instala a dependencia de desenvolvimento. Nas
seguintes, as camadas Docker permanecem em cache. O servidor inicia sem esperar
o VS Code: isso preserva o uso normal da interface enquanto o depurador nao
esta anexado. Depois de conectar, qualquer requisicao que alcance um breakpoint
em uma **linha executavel** sera interrompida. Nao use a linha `def`: ela foi
executada durante o import do modulo, antes da requisicao. Por exemplo, use uma
linha dentro de `ProdutoRepository.list_familias()` ou `list_products()`.

Para investigar exclusivamente a inicializacao do Flask, adicione
temporariamente `--wait-for-client` apos `--listen` em
`docker-compose.debug.yml`, conecte o VS Code e remova a opcao ao terminar.
Nao a deixe como padrao: enquanto espera o cliente, o endpoint de health nao
responde e o frontend fica sem API.

## Mapeamento e seguranca

- Codigo no computador: `${workspaceFolder}/backend/catalog_server`.
- Codigo no container: `/app/catalog_server`.
- Porta de depuracao: `5678`, vinculada somente a `127.0.0.1`.
- Apenas um processo Flask e iniciado, sem reloader e sem workers Gunicorn.
- O Python usa `-Xfrozen_modules=off`, necessario para breakpoints confiaveis
  com o Python 3.14 da imagem.
- Banco e demais servicos Docker continuam os mesmos do DEV local.

## Restaurar o servidor normal

Ao interromper a sessao pelo VS Code, a tarefa de restauracao e executada
automaticamente. Se o editor for encerrado de forma abrupta, execute
**Terminal > Executar Tarefa > Docker: restaurar backend Gunicorn**. O comando
recria somente o backend DEV com a configuracao normal de
`docker-compose.yml`; nao executa migrations e nao toca em staging ou producao.

## Diagnostico rapido

Se o breakpoint ficar cinza, confira se o VS Code abriu a raiz do projeto e se
o arquivo esta dentro de `backend/catalog_server/`. Apos pressionar `F5`, a
barra de depuracao deve indicar uma sessao ativa. Se a tarefa falhar antes do
attach, ela informara que a porta nao abriu; nao prossiga com a navegacao ate
ela concluir. Para conferir o listener:

```powershell
docker compose -f docker-compose.yml -f docker-compose.debug.yml logs backend
Test-NetConnection 127.0.0.1 -Port 5678
```

Se a porta estiver ocupada, encerre o processo local que a utiliza ou altere a
porta nos dois arquivos: `docker-compose.debug.yml` e `.vscode/launch.json`.
