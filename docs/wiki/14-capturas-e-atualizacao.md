# Capturas de tela e atualização da wiki

## Regra das capturas

Cada módulo deve ter captura real do DEV, com a mesma versão indicada no topo
da wiki. A captura deve mostrar a tela, os campos relevantes e, quando fizer
sentido, estados de sucesso, vazio, erro e aprovação. Telas responsivas devem
ter evidência desktop e mobile/tablet.

As capturas da própria central de ajuda estão disponíveis em:

- `capturas/manual-central-dev.png` — desktop, consulta pública;
- `capturas/manual-central-mobile-dev.png` — viewport móvel, consulta pública.

As capturas autenticadas das rotas, ações e subtelas estão indexadas em
[`capturas/README.md`](capturas/README.md). Elas foram realizadas no DEV com
dados anonimizados no DOM e sem confirmar operações destrutivas. A captura de
Relatórios registra “Sem acesso” para o administrador como evidência de uma
pendência funcional de RBAC.

## Segurança

Antes de salvar uma imagem, conferir que não há senha, token, certificado,
documento real, telefone real, endereço, e-mail pessoal ou valor financeiro
sensível. Use apenas massa de demonstração anonimizada.

## Convenção

```text
docs/wiki/capturas/<modulo>-desktop-dev.png
docs/wiki/capturas/<modulo>-mobile-dev.png
docs/wiki/capturas/<modulo>-<acao>-desktop-dev.png
```

Os capítulos devem usar legenda no formato “Figura N — tela X, versão Y, estado
Z”. A imagem não deve substituir o passo a passo textual.

## Checklist de publicação

- Rotas e links da wiki abrem a tela correspondente.
- Imagens existem, carregam e não expõem dado sensível.
- Atalhos foram verificados na versão indicada.
- Permissões e segregação foram testadas com perfis adequados.
- Texto coincide com contrato da API e comportamento do backend.
- Data, versão e pendências de captura estão registradas.
