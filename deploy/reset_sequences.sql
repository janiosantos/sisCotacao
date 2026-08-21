-- Recalcula as sequencias para ficarem acima do maior id existente.
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT seq.oid::regclass AS seqname,
           tbl.oid::regclass AS tblname,
           att.attname        AS colname
    FROM pg_class seq
    JOIN pg_namespace ns ON ns.oid = seq.relnamespace
    JOIN pg_depend d ON d.objid = seq.oid AND d.deptype = 'a'
    JOIN pg_class tbl ON tbl.oid = d.refobjid
    JOIN pg_attribute att ON att.attrelid = tbl.oid AND att.attnum = d.refobjsubid
    WHERE seq.relkind = 'S' AND ns.nspname = 'public'
  LOOP
    EXECUTE format(
      'SELECT setval(%L, GREATEST((SELECT COALESCE(MAX(%I), 1) FROM %s), nextval(%L)))',
      r.seqname, r.colname, r.tblname, r.seqname
    );
  END LOOP;
END $$;