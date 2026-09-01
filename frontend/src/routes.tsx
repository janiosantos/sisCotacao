// routes.tsx — registro central de rotas com code-splitting por tela.

import { lazy, type ComponentType, type LazyExoticComponent } from "react";

export interface RouteDef {
  pattern: RegExp;
  title: string;
  component?: LazyExoticComponent<ComponentType>;
  recurso?: string;
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
const Relatorios = lazy(() => import("./pages/relatorios"));
const Webhooks = lazy(() => import("./pages/webhooks"));
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
const Atualizacoes = lazy(() => import("./pages/atualizacoes"));
const Perfis = lazy(() => import("./pages/perfis"));

export const ROUTES: RouteDef[] = [
  { pattern: /^#\/dashboard$/, title: "Painel", component: Dashboard, recurso: "dashboard" },
  { pattern: /^#\/catalogo$/, title: "Catálogo", component: Catalogo, recurso: "catalogo" },
  { pattern: /^#\/compras$/, title: "Compras", component: Compras, recurso: "compras" },
  { pattern: /^#\/produtos$/, title: "Produtos", component: Produtos, recurso: "produtos" },
  {
    pattern: /^#\/produtos\/novo$/,
    title: "Novo produto",
    component: ProdutoEditor,
    recurso: "produtos",
  },
  {
    pattern: /^#\/produtos\/(\d+)$/,
    title: "Produto",
    component: ProdutoEditor,
    recurso: "produtos",
  },
  { pattern: /^#\/cotacoes$/, title: "Cotações", component: Cotacoes, recurso: "cotacoes" },
  {
    pattern: /^#\/cotacoes\/(\d+)$/,
    title: "Cotação",
    component: CotacoesDetalhe,
    recurso: "cotacoes",
  },
  { pattern: /^#\/pre-venda$/, title: "Pré-venda", component: Pdv, recurso: "pre-venda" },
  { pattern: /^#\/estoque$/, title: "Estoque", component: Estoque, recurso: "estoque" },
  { pattern: /^#\/relatorios$/, title: "Relatórios", component: Relatorios, recurso: "relatorios" },
  { pattern: /^#\/posvenda$/, title: "Pós-venda", component: PosVenda, recurso: "posvenda" },
  { pattern: /^#\/bancos$/, title: "Bancos", component: Bancos, recurso: "bancos" },
  { pattern: /^#\/webhooks$/, title: "Webhooks", component: Webhooks, recurso: "financeiro" },
  { pattern: /^#\/fiscal$/, title: "Fiscal", component: Fiscal, recurso: "fiscal" },
  { pattern: /^#\/financeiro$/, title: "Financeiro", component: Financeiro, recurso: "financeiro" },
  { pattern: /^#\/caixa$/, title: "Caixa", component: Caixa, recurso: "caixa" },
  { pattern: /^#\/precos$/, title: "Preços", component: Precos, recurso: "precos" },
  { pattern: /^#\/orcamentos$/, title: "Orçamentos", component: Orcamentos, recurso: "orcamentos" },
  { pattern: /^#\/solicitacoes$/, title: "Solicitações de Compra", component: Solicitacoes, recurso: "solicitacoes" },
  { pattern: /^#\/categorias$/, title: "Categorias", component: Categorias, recurso: "categorias" },
  { pattern: /^#\/unidades$/, title: "Unidades", component: Unidades, recurso: "unidades" },
  {
    pattern: /^#\/diagnostico-variacoes$/,
    title: "Qualidade do Catálogo",
    component: Diagnostico,
    recurso: "qualidade",
  },
  { pattern: /^#\/fornecedores$/, title: "Fornecedores", component: Fornecedores, recurso: "fornecedores" },
  { pattern: /^#\/historico$/, title: "Histórico de Preços", component: Historico, recurso: "historico" },
  { pattern: /^#\/clientes$/, title: "Clientes", component: Clientes, recurso: "clientes" },
  { pattern: /^#\/vendedores$/, title: "Vendedores", component: Vendedores, recurso: "vendedores" },
  { pattern: /^#\/usuarios$/, title: "Usuários", component: Usuarios, recurso: "usuarios" },
  { pattern: /^#\/perfis$/, title: "Perfis e permissões", component: Perfis, recurso: "perfis" },
  { pattern: /^#\/plano-contas$/, title: "Plano de Contas", component: PlanoContas, recurso: "plano_contas" },
  { pattern: /^#\/configuracoes$/, title: "Configurações", component: Configuracoes, recurso: "configuracoes" },
  { pattern: /^#\/atualizacoes$/, title: "Atualizações", component: Atualizacoes, recurso: "atualizacoes" },
];
