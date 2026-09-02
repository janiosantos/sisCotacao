# Capturas de tela e atualização da wiki

## Regra das capturas

Cada módulo deve ter captura real do DEV, com a mesma versão indicada no topo
da wiki. A captura deve mostrar a tela, os campos relevantes e, quando fizer
sentido, estados de sucesso, vazio, erro e aprovação. Telas responsivas devem
ter evidência desktop e mobile/tablet.

As capturas da própria central de ajuda já estão disponíveis em:

- `capturas/manual-central-dev.png` — desktop, consulta pública;
- `capturas/manual-central-mobile-dev.png` — viewport móvel, consulta pública.

As capturas autenticadas de cada módulo ainda dependem de o proxy DEV `/api`
estar disponível e de uma massa de demonstração aprovada. Enquanto isso, cada
capítulo mantém o procedimento textual e não deve apresentar uma imagem
genérica como se fosse evidência da tela operacional.

## Segurança

Antes de salvar uma imagem, conferir que não há senha, token, certificado,
documento real, telefone real, endereço, e-mail pessoal ou valor financeiro
sensível. Use apenas massa de demonstração anonimizada.

## Convenção

```text
docs/wiki/capturas/<modulo>-desktop.png
docs/wiki/capturas/<modulo>-mobile.png
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
