# Galeria de produtos

Aplicacao standalone para preservar e reutilizar as imagens do catalogo
anterior. Em producao, todo este pacote e instalado em
`/home/jpsantos/galeria-produtos`, fora do checkout do SISCOM.

O banco `data/gallery.sqlite3` e a arvore `data/media/` sao produzidos pelo
exportador `python -m catalog_server.pre_go_live export-images`. A aplicacao
nao acessa o PostgreSQL do ERP e monta os dados somente para leitura.

O acesso do operador usa uma sessao HMAC de curta duracao emitida pelo ERP.
A importacao usa um token de servico derivado do mesmo segredo, sem aceitar
URLs ou caminhos arbitrarios informados pelo navegador.
