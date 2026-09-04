# PROBLEM

- **Severidade:** média
- **Categoria:** ponto fraco
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/Dockerfile:1-25`; `pyproject.toml:1-29`; `uv.lock`

## Explicação para leigos

Embora o projeto possua um arquivo que fixa as versões das bibliotecas, a imagem do backend ignora esse arquivo e baixa versões abertas diretamente. Duas imagens construídas em dias diferentes podem se comportar de maneiras diferentes usando o mesmo código.

## Evidência e análise técnica

`uv.lock` está versionado e `pyproject.toml` declara as dependências. O Dockerfile copia apenas `pyproject.toml`, mas executa uma lista manual de `pip install` com pacotes sem versões exatas. A lista duplica o manifesto e pode ficar incompleta quando um import ou dependência for adicionado.

Isso também quebra a propriedade de release imutável: a tag da aplicação não determina integralmente as versões instaladas.

## Impacto

Builds podem falhar ou introduzir regressões e vulnerabilidades sem mudança no repositório. DEV, CI, staging e produção podem testar conjuntos diferentes de bibliotecas.

## Solução proposta

Copiar `uv.lock` e instalar com resolução congelada (`uv sync --frozen`) ou exportar requisitos hashados a partir do lock. Separar grupos runtime/dev sem duplicar manualmente a lista. O pipeline deve falhar se `pyproject.toml` e o lock estiverem dessincronizados.

Reconstruir posteriormente duas vezes a imagem e comparar inventário/SBOM; nenhum build foi executado nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/Dockerfile b/backend/Dockerfile
@@
 COPY pyproject.toml pyproject.toml
+COPY uv.lock uv.lock
@@
-RUN pip install --no-cache-dir flask python-dotenv requests ...
+RUN pip install --no-cache-dir uv && \
+    uv sync --frozen --no-dev --no-install-project
```
