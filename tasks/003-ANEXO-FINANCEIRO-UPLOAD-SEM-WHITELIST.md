# PROBLEM
- **Severidade:** alta
- **Categoria:** segurança
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/blueprints/api_financeiro.py:638-664`, `backend/catalog_server/app_factory.py:483-485`

## Explicação para leigos
O upload de anexos financeiros aceita qualquer extensão e publica o arquivo em um diretório servido diretamente pelo endpoint de imagens. Um usuário autorizado pode enviar HTML, SVG ou outro conteúdo ativo que será armazenado e posteriormente aberto no mesmo domínio do ERP.

## Evidência e análise técnica
`anexar_documento()` usa a extensão original de `arquivo.filename` sem normalizar ou validar tipo, lê o conteúdo sem validar assinatura e salva com `os.path.join(base, filename)`. O nome final conserva a extensão. Em contraste, o upload de comprovantes em `api_payments.py` possui whitelist e verificação de magic bytes. O `app_factory` serve `/images/<path:name>` sem autenticação.

## Impacto
Há risco de stored XSS e de distribuição de arquivos não autorizados. Um HTML salvo como anexo pode executar JavaScript no contexto do domínio do ERP quando aberto pelo navegador. Arquivos malformados também podem consumir espaço e gerar problemas de disponibilidade, apesar do limite global de request.

## Solução proposta
Aplicar uma política comum de upload: whitelist por finalidade, extensão derivada do conteúdo, validação de magic bytes, limite específico, nome opaco e armazenamento fora da raiz pública. Criar endpoint autenticado de download com `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` e checagem de permissão sobre a conta. Apagar o arquivo se a transação do registro falhar e adicionar varredura opcional de malware.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ api_financeiro.py
-    ext = os.path.splitext(arquivo.filename)[1] or ".pdf"
+    ext = validar_anexo_financeiro(arquivo)  # somente pdf/png/jpg, magic bytes
+    base = diretorio_privado_de_anexos()
+    filename = nome_opaco(ext)
+    # salvar fora de IMAGES_DIR; download passa por autorização
```

