// main.ts — roteador simples por hash (mesmo comportamento de app.js).

import "./styles/tokens.css";
import "./styles/base.css";

import { render as renderHistorico } from "./pages/historico";

const $app = document.getElementById("app");
const $navLinks = document.querySelectorAll<HTMLAnchorElement>("#mainNav a");
if (!$app) throw new Error("Elemento #app não encontrado");

interface Route {
  pattern: RegExp;
  handler: (m: RegExpMatchArray) => void | Promise<void>;
  tab: string;
}

const routes: Route[] = [
  { pattern: /^#\/catalogo$/, handler: () => renderPlaceholder("Catálogo"), tab: "catalogo" },
  { pattern: /^#\/compras$/, handler: () => renderPlaceholder("Comprar"), tab: "compras" },
  { pattern: /^#\/produtos$/, handler: () => renderPlaceholder("Produtos"), tab: "produtos" },
  { pattern: /^#\/cotacoes$/, handler: () => renderPlaceholder("Cotações"), tab: "cotacoes" },
  { pattern: /^#\/fornecedores$/, handler: () => renderPlaceholder("Fornecedores"), tab: "fornecedores" },
  { pattern: /^#\/historico$/, handler: () => renderHistorico($app), tab: "historico" },
];

function renderPlaceholder(titulo: string): void {
  if (!$app) return;
  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">${titulo}</h1>
        <p class="page-sub">Página migrada para Vite+TS nesta ietapa — em breve.</p>
      </div>
    </div>
  `;
}

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