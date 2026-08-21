-- Apaga os dados de todas as tabelas do schema public, preservando o
-- schema e o registro de migracoes (schema_migrations).
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT quote_ident(tablename) AS tbl
    FROM pg_tables
    WHERE schemaname = 'public' AND tablename <> 'schema_migrations'
  LOOP
    EXECUTE 'TRUNCATE TABLE ' || r.tbl || ' CASCADE';
  END LOOP;
END $$;