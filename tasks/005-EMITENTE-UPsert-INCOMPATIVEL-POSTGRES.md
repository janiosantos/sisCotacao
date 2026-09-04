# PROBLEM
- **Severidade:** alta
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/repositories/fiscal_avancado.py:17-38`, `backend/catalog_server/pgsql.py:216-255`

## Explicação para leigos
Ao cadastrar o primeiro emitente fiscal, o código tenta descobrir o ID usando uma função específica do SQLite. O ERP, porém, usa exclusivamente PostgreSQL.

## Evidência e análise técnica
Depois de `INSERT INTO emitente`, `EmitenteRepository.upsert()` executa `SELECT last_insert_rowid()`. O tradutor SQL de `pgsql.py` converte placeholders e alguns comandos SQLite, mas não implementa `last_insert_rowid()`. O shim já oferece `.lastrowid` para inserts sem `RETURNING`, portanto o trecho é uma exceção incompatível com o banco declarado como oficial.

## Impacto
O cadastro inicial ou a recriação do emitente pode falhar no PostgreSQL. Isso bloqueia configuração fiscal e pode deixar o operador sem conseguir iniciar emissão de documentos, apesar de o formulário parecer correto.

## Solução proposta
Usar `INSERT ... RETURNING id` explicitamente, ou obter `.lastrowid` do cursor do shim. Alinhar todos os repositórios ao mesmo contrato PostgreSQL e adicionar teste de banco vazio para `upsert()` seguido de `get()`, incluindo rollback quando a inserção falhar.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ fiscal_avancado.py
-            conn.execute(f"INSERT INTO emitente ({cols}) VALUES ({placeholders})", list(dados.values()))
-            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
+            cur = conn.execute(
+                f"INSERT INTO emitente ({cols}) VALUES ({placeholders}) RETURNING id",
+                list(dados.values()),
+            )
+            return int(cur.fetchone()[0])
```

