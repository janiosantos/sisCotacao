# AGENTS.md

## Aplicação de patches

Os patches (arquivos `.patch`, normalmente em `PATCH/`) são aplicados **em ordem sequencial**.

- O patch N+1 pode corrigir ou implementar algo introduzido pelo patch N.
- Ao aplicar um patch, **o conteúdo do patch tem prioridade sobre o código já existente**. Em caso de conflito, o patch vence, mesmo que isso reverta ou sobrescreva mudanças de um patch anterior.
- O patch é aplicado **de forma integral, nunca seletiva**: todos os arquivos e todas as mudanças do patch entram. Não usar `--exclude`, não pular hunks nem aplicar só o que "falta". O estado final de cada arquivo tocado pelo patch deve ser exatamente o que o patch produz.
- Técnica recomendada para patches cumulativos (gerados sobre uma base comum, ex.: `ab4fb52`): aplicar o patch completo num worktree limpo na base e sincronizar o resultado integral para o working tree, em vez de aplicar parcialmente.

## Verificação

Depois de aplicar um patch:
- Python: `py_compile` nos arquivos alterados.
- Frontend: `npm run typecheck` (a partir de `frontend/`).
