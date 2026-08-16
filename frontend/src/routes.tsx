// routes.tsx — registro central de rotas com code-splitting por tela.

import { lazy, type ComponentType, type LazyExoticComponent } from "react";

export interface RouteDef {
  pattern: RegExp;
  title: string;
  component?: LazyExoticComponent<ComponentType>;
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
const Caixa = lazy(() => import("./pages/caixa"));
const Precos = lazy(() => import("./pages/precos"));
const Fiscal = lazy(() => import("./pages/fiscal"));
const Orcamentos = lazy(() => import("./pages/orcamentos"));
const Cotacoes = lazy(() => import("./pages/cotacoes"));
const CotacoesDetalhe = lazy(() => import("./pages/cotacoes").then((m) => ({ default: m.CotacoesDetalhe })));
const Catalogo = lazy(() => import("./pages/catalogo"));
const Compras = lazy(() => import("./pages/compras"));
const Produtos = lazy(() => import("./pages/produtos"));
const ProdutoEditor = lazy(() => import("./pages/produtos").then((m) => ({ default: m.ProdutoEditor })));
const Pdv = lazy(() => import("./pages/pre-venda"));
const Configuracoes = lazy(() => import("./pages/configuracoes"));

export const ROUTES: RouteDef[] = [
  { pattern: /^#\/dashboard$/, title: "Painel", component: Dashboard },
  { pattern: /^#\/catalogo$/, title: "Catálogo", component: Catalogo },
  { pattern: /^#\/compras$/, title: "Compras", component: Compras },
  { pattern: /^#\/produtos$/, title: "Produtos", component: Produtos },
  {
    pattern: /^#\/produtos\/novo$/,
    title: "Novo produto",
    component: ProdutoEditor,
  },
  {
    pattern: /^#\/produtos\/(\d+)$/,
    title: "Produto",
    component: ProdutoEditor,
  },
  { pattern: /^#\/cotacoes$/, title: "Cotações", component: Cotacoes },
  {
    pattern: /^#\/cotacoes\/(\d+)$/,
    title: "Cotação",
    component: CotacoesDetalhe,
  },
  { pattern: /^#\/pre-venda$/, title: "Pré-venda", component: Pdv },
  { pattern: /^#\/estoque$/, title: "Estoque", component: Estoque },
  { pattern: /^#\/posvenda$/, title: "Pós-venda", component: PosVenda },
  { pattern: /^#\/bancos$/, title: "Bancos", component: Bancos },
  { pattern: /^#\/fiscal$/, title: "Fiscal", component: Fiscal },
  { pattern: /^#\/financeiro$/, title: "Financeiro", component: Financeiro },
  { pattern: /^#\/caixa$/, title: "Caixa", component: Caixa },
  { pattern: /^#\/precos$/, title: "Preços", component: Precos },
  { pattern: /^#\/orcamentos$/, title: "Orçamentos", component: Orcamentos },
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
  { pattern: /^#\/configuracoes$/, title: "Configurações", component: Configuracoes },
];
