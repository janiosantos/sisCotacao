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

const Dashboard = lazy(() => import("./pages/dashboard"));
const Clientes = lazy(() => import("./pages/clientes"));
const Fornecedores = lazy(() => import("./pages/fornecedores"));
const Vendedores = lazy(() => import("./pages/vendedores"));
const Usuarios = lazy(() => import("./pages/usuarios"));
const Unidades = lazy(() => import("./pages/unidades"));
const Categorias = lazy(() => import("./pages/categorias"));
const PlanoContas = lazy(() => import("./pages/plano_contas"));
const Solicitacoes = lazy(() => import("./pages/solicitacoes"));
const Bancos = lazy(() => import("./pages/bancos"));
const PosVenda = lazy(() => import("./pages/posvenda"));
const Historico = lazy(() => import("./pages/historico"));
const Diagnostico = lazy(() => import("./pages/diagnostico_variacoes"));
const Estoque = lazy(() => import("./pages/estoque"));
const Financeiro = lazy(() => import("./pages/financeiro"));

export const ROUTES: RouteDef[] = [
  { pattern: /^#\/dashboard$/, title: "Painel", component: Dashboard },
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
  { pattern: /^#\/pdv$/, title: "PDV", loader: () => import("./pages/pdv").then((m) => m.render) },
  { pattern: /^#\/estoque$/, title: "Estoque", component: Estoque },
  { pattern: /^#\/posvenda$/, title: "Pós-venda", component: PosVenda },
  { pattern: /^#\/bancos$/, title: "Bancos", component: Bancos },
  { pattern: /^#\/fiscal$/, title: "Fiscal", loader: () => import("./pages/fiscal").then((m) => m.render) },
  { pattern: /^#\/financeiro$/, title: "Financeiro", component: Financeiro },
  { pattern: /^#\/precos$/, title: "Preços", loader: () => import("./pages/precos").then((m) => m.render) },
  { pattern: /^#\/orcamentos$/, title: "Orçamentos", loader: () => import("./pages/orcamentos").then((m) => m.render) },
  { pattern: /^#\/solicitacoes$/, title: "Solicitações de Compra", component: Solicitacoes },
  { pattern: /^#\/categorias$/, title: "Categorias", component: Categorias },
  { pattern: /^#\/unidades$/, title: "Unidades", component: Unidades },
  {
    pattern: /^#\/diagnostico-variacoes$/,
    title: "Qualidade do Catálogo",
    component: Diagnostico,
  },
  { pattern: /^#\/fornecedores$/, title: "Fornecedores", component: Fornecedores },
  { pattern: /^#\/historico$/, title: "Histórico de Preços", component: Historico },
  { pattern: /^#\/clientes$/, title: "Clientes", component: Clientes },
  { pattern: /^#\/vendedores$/, title: "Vendedores", component: Vendedores },
  { pattern: /^#\/usuarios$/, title: "Usuários", component: Usuarios },
  { pattern: /^#\/plano-contas$/, title: "Plano de Contas", component: PlanoContas },
];
