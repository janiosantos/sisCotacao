// main.ts — roteador simples por hash (mesmo comportamento de app.js).

import "./styles/tokens.css";
import "./styles/base.css";

import { render as renderCatalogo } from "./pages/catalogo";
import { render as renderCompras, registrarImportadorIA } from "./pages/compras";
import { render as renderFornecedores } from "./pages/fornecedores";
import { render as renderHistorico } from "./pages/historico";
import { renderLista as renderProdutosLista, renderEditor as renderProdutosEditor } from "./pages/produtos";
import { renderLista as renderCotacoesLista, renderDetalhe as renderCotacoesDetalhe } from "./pages/cotacoes";
import { abrir as abrirImportia } from "./pages/importia";
import { injectOverlay as injectCartOverlay } from "./cart";

const $app = document.getElementById("app");
const $navLinks = document.querySelectorAll<HTMLAnchorElement>("#mainNav a");
if (!$app) throw new Error("Elemento #app não encontrado");

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
  { pattern: /^#\/fornecedores$/, handler: () => renderFornecedores($app), tab: "fornecedores" },
  { pattern: /^#\/historico$/, handler: () => renderHistorico($app), tab: "historico" },
];

function resolve(): void {
  const hash = location.hash || "#/catalogo";
  for (const r of routes) {
    const m = hash.match(r.pattern);
    if (m) {
      $navLinks.forEach((a) => a.classList.toggle("is-active", a.dataset.route === r.tab));
      window.scrollTo(0, 0);
      void r.handler(m);
      return;
    }
  }
  location.hash = "#/catalogo";
}

window.addEventListener("hashchange", resolve);
window.addEventListener("DOMContentLoaded", resolve);

registrarImportadorIA(abrirImportia);
injectCartOverlay();
