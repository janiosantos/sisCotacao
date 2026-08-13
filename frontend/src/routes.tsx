// routes.tsx — registro central de rotas com code-splitting por tela.
// - Telas React (componentes) usam React.lazy.
// - Telas legadas (TS puro) usam um `loader` que importa o módulo e devolve a
//   função `render` — o LegacyPage/LazyVanillaPage (App.tsx) a executa dentro
//   do chrome "legacy".

import { lazy, type ComponentType, type LazyExoticComponent, type ReactNode } from "react";

export interface SidebarActionDef {
  icon?: ReactNode;
  label: string;
  shortcut?: string;
  action?: () => void;
}

export type PageRenderer = (el: HTMLElement, m: RegExpMatchArray) => void | Promise<void>;

export interface RouteDef {
  pattern: RegExp;
  title: string;
  component?: LazyExoticComponent<ComponentType>;
  loader?: () => Promise<PageRenderer>;
  actions?: SidebarActionDef[];
}

const PreVenda = lazy(() => import("./pages/PreVenda"));
const PdvPage = lazy(() => import("./pages/PdvPage"));

export const ROUTES: RouteDef[] = [
  { pattern: /^#\/dashboard$/, title: "Painel", loader: () => import("./pages/dashboard").then((m) => m.render) },
  { pattern: /^#\/prevenda$/, title: "Pré-Venda", component: PreVenda },
  { pattern: /^#\/catalogo$/, title: "Catálogo", loader: () => import("./pages/catalogo").then((m) => m.render) },
  { pattern: /^#\/compras$/, title: "Compras", loader: () => import("./pages/compras").then((m) => m.render) },
  { pattern: /^#\/produtos$/, title: "Produtos", loader: () => import("./pages/produtos").then((m) => m.renderLista) },
  {
    pattern: /^#\/produtos\/novo$/,
    title: "Novo produto",
    loader: () => import("./pages/produtos").then((m) => (el) => m.renderEditor(el, null)),
  },
  {
    pattern: /^#\/produtos\/(\d+)$/,
    title: "Produto",
    loader: () => import("./pages/produtos").then((m) => (el, mm) => m.renderEditor(el, Number(mm[1]))),
  },
  { pattern: /^#\/cotacoes$/, title: "Cotações", loader: () => import("./pages/cotacoes").then((m) => m.renderLista) },
  {
    pattern: /^#\/cotacoes\/(\d+)$/,
    title: "Cotação",
    loader: () => import("./pages/cotacoes").then((m) => (el, mm) => m.renderDetalhe(el, Number(mm[1]))),
  },
  { pattern: /^#\/pdv$/, title: "PDV", component: PdvPage },
  { pattern: /^#\/estoque$/, title: "Estoque", loader: () => import("./pages/estoque").then((m) => m.render) },
  { pattern: /^#\/posvenda$/, title: "Pós-venda", loader: () => import("./pages/posvenda").then((m) => m.render) },
  { pattern: /^#\/bancos$/, title: "Bancos", loader: () => import("./pages/bancos").then((m) => m.render) },
  { pattern: /^#\/fiscal$/, title: "Fiscal", loader: () => import("./pages/fiscal").then((m) => m.render) },
  { pattern: /^#\/financeiro$/, title: "Financeiro", loader: () => import("./pages/financeiro").then((m) => m.render) },
  { pattern: /^#\/precos$/, title: "Preços", loader: () => import("./pages/precos").then((m) => m.render) },
  { pattern: /^#\/orcamentos$/, title: "Orçamentos", loader: () => import("./pages/orcamentos").then((m) => m.render) },
  { pattern: /^#\/solicitacoes$/, title: "Solicitações de Compra", loader: () => import("./pages/solicitacoes").then((m) => m.render) },
  { pattern: /^#\/categorias$/, title: "Categorias", loader: () => import("./pages/categorias").then((m) => m.render) },
  { pattern: /^#\/unidades$/, title: "Unidades", loader: () => import("./pages/unidades").then((m) => m.render) },
  {
    pattern: /^#\/diagnostico-variacoes$/,
    title: "Qualidade do Catálogo",
    loader: () => import("./pages/diagnostico_variacoes").then((m) => m.render),
  },
  { pattern: /^#\/fornecedores$/, title: "Fornecedores", loader: () => import("./pages/fornecedores").then((m) => m.render) },
  { pattern: /^#\/historico$/, title: "Histórico de Preços", loader: () => import("./pages/historico").then((m) => m.render) },
  { pattern: /^#\/clientes$/, title: "Clientes", loader: () => import("./pages/clientes").then((m) => m.render) },
  { pattern: /^#\/vendedores$/, title: "Vendedores", loader: () => import("./pages/vendedores").then((m) => m.render) },
  { pattern: /^#\/usuarios$/, title: "Usuários", loader: () => import("./pages/usuarios").then((m) => m.render) },
  { pattern: /^#\/plano-contas$/, title: "Plano de Contas", loader: () => import("./pages/plano_contas").then((m) => m.render) },
];
