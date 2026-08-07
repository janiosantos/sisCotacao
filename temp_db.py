import sqlite3
c = sqlite3.connect("catalog_server/data/server.db")
n = c.execute("SELECT COUNT(*) FROM paginas_fonte").fetchone()[0]
tot = c.execute("SELECT SUM(length(html)) FROM paginas_fonte").fetchone()[0]
avg = tot//n if n else 0
print("paginas_fonte:", n, "| total html bytes: %.1f MB" % (tot/1e6), "| avg: %.1f KB" % (avg/1e3))
# tamanho de todas as tabelas somando lengths
rows = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'produtos_fts%'").fetchall()
print("\n== tamanho aproximado por tabela (bytes de colunas de texto) ==")
for (t,) in rows:
    try:
        sz = c.execute("SELECT SUM(length(row(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28))) FROM "+t).fetchone()[0] or 0
    except Exception:
        sz = 0
    print(f"  {t:28s} {sz/1e6:10.1f} MB")
