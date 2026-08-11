// main.ts — roteador simples por hash (mesmo comportamento de app.js).

import "./styles/tokens.css";
import "./styles/base.css";

import { render as renderCatalogo } from "./pages/catalogo";
import { render as renderClientes } from "./pages/clientes";
import { render as renderCompras, registrarImportadorIA } from "./pages/compras";
import { render as renderSolicitacoes } from "./pages/solicitacoes";
import { render as renderFornecedores } from "./pages/fornecedores";
import { render as renderHistorico } from "./pages/historico";
import { render as renderCategorias } from "./pages/categorias";
import { render as renderUnidades } from "./pages/unidades";
import { render as renderDiagnostico } from "./pages/diagnostico_variacoes";
import { renderLista as renderProdutosLista, renderEditor as renderProdutosEditor } from "./pages/produtos";
import { renderLista as renderCotacoesLista, renderDetalhe as renderCotacoesDetalhe } from "./pages/cotacoes";
import { render as renderPrecos } from "./pages/precos";
import { render as renderPdv } from "./pages/pdv";
import { render as renderOrcamentos } from "./pages/orcamentos";
import { render as renderPlanoContas } from "./pages/plano_contas";
import { render as renderUsuarios } from "./pages/usuarios";
import { render as renderPosVenda } from "./pages/posvenda";
import { render as renderBancos } from "./pages/bancos";
import { render as renderFiscal } from "./pages/fiscal";
import { render as renderFinanceiro } from "./pages/financeiro";
import { render as renderEstoque } from "./pages/estoque";
import { render as renderVendedores } from "./pages/vendedores";
import { renderLogin, carregarSessao, estaAutenticado } from "./pages/login";
import { startupAuth } from "./auth";
import { abrir as abrirImportia } from "./pages/importia";
import { injectOverlay as injectCartOverlay } from "./cart";

const $app = document.getElementById("app");
const $navLinks = document.querySelectorAll<HTMLAnchorElement>("#mainNav a");
const $navToggles = document.querySelectorAll<HTMLElement>(".nav-toggle");
if (!$app) throw new Error("Elemento #app não encontrado");

function fecharTodosMenus(): void {
  document.querySelectorAll<HTMLElement>(".nav-sub").forEach((s) => s.classList.remove("is-open"));
}

fecharTodosMenus();

$navToggles.forEach((btn) => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const group = btn.dataset.group || "";
    const sub = document.querySelector<HTMLElement>(`.nav-sub[data-group="${group}"]`);
    const jaAberto = sub?.classList.contains("is-open");
    fecharTodosMenus();
    if (!jaAberto) sub?.classList.add("is-open");
  });
});

// Fecha menus ao clicar fora
document.addEventListener("click", () => fecharTodosMenus());
document.querySelectorAll<HTMLElement>(".nav-group, .nav-sub").forEach((el) => {
  el.addEventListener("click", (e) => e.stopPropagation());
});

interface Route {
  pattern: RegExp;
  handler: (m: RegExpMatchArray) => void | Promise<void>;
  tab: string;
}

const routes: Route[] = [
  { pattern: /^#\/catalogo$/, handler: () => renderCatalogo($app), tab: "catalogo" },
  { pattern: /^#\/compras$/, handler: () => renderCompras($app), tab: "compras" },
  { pattern: /^#\/produtos$/, handler: () => renderProdutosLista($app), tab: "produtos" },
  { pattern: /^#\/produtos\/novo$/, handler: () => renderProdutosEditor($app, null), tab: "produtos" },
  { pattern: /^#\/produtos\/(\d+)$/, handler: (m) => renderProdutosEditor($app, Number(m[1])), tab: "produtos" },
  { pattern: /^#\/cotacoes$/, handler: () => renderCotacoesLista($app), tab: "cotacoes" },
  { pattern: /^#\/cotacoes\/(\d+)$/, handler: (m) => renderCotacoesDetalhe($app, Number(m[1])), tab: "cotacoes" },
  { pattern: /^#\/pdv$/, handler: () => renderPdv($app), tab: "pdv" },
  { pattern: /^#\/estoque$/, handler: () => renderEstoque($app), tab: "estoque" },
  { pattern: /^#\/posvenda$/, handler: () => renderPosVenda($app), tab: "posvenda" },
  { pattern: /^#\/bancos$/, handler: () => renderBancos($app), tab: "bancos" },
  { pattern: /^#\/fiscal$/, handler: () => renderFiscal($app), tab: "fiscal" },
  { pattern: /^#\/financeiro$/, handler: () => renderFinanceiro($app), tab: "financeiro" },
  { pattern: /^#\/precos$/, handler: () => renderPrecos($app), tab: "precos" },
  { pattern: /^#\/orcamentos$/, handler: () => renderOrcamentos($app), tab: "orcamentos" },
  { pattern: /^#\/solicitacoes$/, handler: () => renderSolicitacoes($app), tab: "solicitacoes" },
  { pattern: /^#\/categorias$/, handler: () => renderCategorias($app), tab: "categorias" },
  { pattern: /^#\/unidades$/, handler: () => renderUnidades($app), tab: "unidades" },
  { pattern: /^#\/diagnostico-variacoes$/, handler: () => renderDiagnostico($app), tab: "diagnostico-variacoes" },
  { pattern: /^#\/fornecedores$/, handler: () => renderFornecedores($app), tab: "fornecedores" },
  { pattern: /^#\/historico$/, handler: () => renderHistorico($app), tab: "historico" },
  { pattern: /^#\/clientes$/, handler: () => renderClientes($app), tab: "clientes" },
  { pattern: /^#\/vendedores$/, handler: () => renderVendedores($app), tab: "vendedores" },
  { pattern: /^#\/usuarios$/, handler: () => renderUsuarios($app), tab: "usuarios" },
  { pattern: /^#\/plano-contas$/, handler: () => renderPlanoContas($app), tab: "plano-contas" },
];

let gated = false;

function resolve(): void {
  const autenticado = estaAutenticado();
  if (!autenticado) {
    renderLogin($app!);
    $navLinks.forEach((a) => a.classList.remove("is-active"));
    void startupAuth();
    gated = true;
    return;
  }
  if (gated) {
    gated = false;
    location.hash = "#/catalogo";
  }
  const hash = location.hash || "#/catalogo";
  for (const r of routes) {
    const m = hash.match(r.pattern);
    if (m) {
      $navLinks.forEach((a) => a.classList.toggle("is-active", a.dataset.route === r.tab));
      fecharTodosMenus();
      window.scrollTo(0, 0);
      void r.handler(m);
      return;
    }
  }
  location.hash = "#/catalogo";
}

let booted = false;
async function boot(): Promise<void> {
  if (booted) return;
  booted = true;
  await carregarSessao();
  resolve();
}

window.addEventListener("hashchange", resolve);
window.addEventListener("DOMContentLoaded", () => void boot());

registrarImportadorIA(abrirImportia);
injectCartOverlay();
