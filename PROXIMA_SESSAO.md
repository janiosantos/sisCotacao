# Retomada — Migração para Tailwind (próxima sessão)

## Estado atual
- Branch: `feature/layout-legacy-react` (commit `1d90b3b` já empurrado).
- Shell Tailwind (sidebar + topbar) + componentes em `frontend/src/ui/ui.tsx` + Tailwind v4 + `lucide-react`.

## Telas JÁ convertidas (React + Tailwind)
dashboard, clientes, fornecedores, vendedores, usuarios, unidades, categorias,
plano_contas, solicitacoes, bancos, posvenda, historico, diagnostico_variacoes,
estoque, financeiro.

## Telas RESTANTES (ainda `.ts`, rodam no shell via adaptador)
`precos`, `fiscal`, `orcamentos`, `cotacoes`, `catalogo`, `compras`, `produtos`, `pdv`

Ordem recomendada:
`precos` → `fiscal` → `orcamentos` → `cotacoes` → `catalogo` → `compras` → `produtos` → `pdv`

## Padrão de conversão (uma página por vez)
1. Ler `frontend/src/pages/X.ts`.
2. Criar `frontend/src/pages/X.tsx` com `export default function X()` usando os
   componentes de `../ui/ui` (Button, Table/THead/TBody/Cell, Modal, Field, Input,
   Select, Textarea, Badge, PageHeader, Loading, EmptyRow, StatCard, Card).
3. Deletar `frontend/src/pages/X.ts`.
4. Em `frontend/src/routes.tsx`:
   - adicionar `const X = lazy(() => import("./pages/X"));`
   - trocar `loader: () => import("./pages/X").then((m) => m.render)` por `component: X`.
5. Rodar `npm run typecheck` e `npm run build` (na pasta `frontend`).

## Comandos úteis
```powershell
cd frontend
npm run dev          # dev server (:5173, proxy /api -> :8000)
npm run typecheck
npm run build
```

## Observações
- `login.ts` e `importia.ts` ficam como `.ts` de propósito (util/modal, não são rotas).
- O container de dev do Docker (`:5173`) precisa ser reconstruído para instalar as
  dependências novas (React, Tailwind, lucide-react) — `docker compose up -d --build frontend`.
- Cada página usa `api.*` de `../api/client`; `toast` de `../ui/dom`; formatação de `../ui/format`.
