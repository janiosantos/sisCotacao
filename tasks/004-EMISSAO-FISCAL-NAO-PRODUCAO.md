# PROBLEM
- **Severidade:** crítica
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/services/nfe_gerador.py:36-78`, `backend/catalog_server/services/nfe_gerador.py:94-175`, `backend/catalog_server/repositories/fiscal_avancado.py:41-73`, `backend/migrations/sql/postgres_schema.sql:799-816`

## Explicação para leigos
O gerador de NF-e/NFC-e ainda monta uma nota estrutural, não uma emissão fiscal segura para operação real. A chave usa ano/mês fixos, alguns campos obrigatórios recebem valores vazios ou fictícios e duas emissões concorrentes podem escolher o mesmo número.

## Evidência e análise técnica
`gerar_chave()` recebe `aamm = "0000"`, usa o CNPJ sem normalização e calcula o código numérico a partir apenas do número. O gerador usa município `0000000`, documento de consumidor `00000000000`, CFOP vazio quando não houver snapshot e códigos tributários simplificados. `NfeSaidaRepository.emitir()` só incrementa `proximo_numero_nfe` depois que o gerador já leu o número em outra conexão. A tabela `nfe_saida` não possui restrição única aparente para `(serie, numero, ambiente/modelo)`.

## Impacto
A nota pode ser rejeitada pela SEFAZ, gerar chave inválida ou duplicada, e o documento armazenado pode divergir da numeração fiscal oficial. Sob concorrência, duas requisições podem gerar a mesma numeração. Isso compromete fiscal, contabilidade, rastreabilidade e eventual cancelamento.

## Solução proposta
Tratar a emissão como um agregado transacional: reservar número por série/modelo/ambiente com `SELECT ... FOR UPDATE`, normalizar e validar CNPJ/UF/IBGE/documentos, montar a chave conforme leiaute vigente, validar XSD antes do envio, controlar idempotência por orçamento e operação, persistir estados de autorização/rejeição e impedir produção enquanto homologação não estiver aprovada. A implementação deve usar o adapter fiscal oficial como fonte única, sem manter um segundo gerador simplificado concorrente.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ nfe_gerador.py
-    aamm = "0000"
+    aamm = data_emissao.strftime("%y%m")
+    validar_contexto_fiscal(emit, destinatario, snapshots)
@@ fiscal_avancado.py
+with conn.transaction():
+    numero = reservar_numero(conn, serie, modelo, ambiente)
+    documento = emitir_idempotente(conn, orcamento_id, modelo, numero)
```

