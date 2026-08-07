// app.js — roteador simples por hash.
(function () {
  const $app = document.getElementById("app");
  const $navLinks = document.querySelectorAll("#mainNav a");

  const routes = [
    { pattern: /^#\/catalogo$/, handler: () => PageCatalogo.render($app), tab: "catalogo" },
    { pattern: /^#\/compras$/, handler: () => PageCompras.render($app), tab: "compras" },
    { pattern: /^#\/produtos$/, handler: () => PageProdutos.renderLista($app), tab: "produtos" },
    { pattern: /^#\/produtos\/novo$/, handler: () => PageProdutos.renderEditor($app, null), tab: "produtos" },
    { pattern: /^#\/produtos\/(\d+)$/, handler: (m) => PageProdutos.renderEditor($app, Number(m[1])), tab: "produtos" },
    { pattern: /^#\/cotacoes$/, handler: () => PageCotacoes.renderLista($app), tab: "cotacoes" },
    { pattern: /^#\/cotacoes\/(\d+)$/, handler: (m) => PageCotacoes.renderDetalhe($app, Number(m[1])), tab: "cotacoes" },
    { pattern: /^#\/fornecedores$/, handler: () => PageFornecedores.render($app), tab: "fornecedores" },
    { pattern: /^#\/historico$/, handler: () => PageHistorico.render($app), tab: "historico" },
  ];

  function resolve() {
    const hash = location.hash || "#/catalogo";
    for (const r of routes) {
      const m = hash.match(r.pattern);
      if (m) {
        $navLinks.forEach((a) => a.classList.toggle("is-active", a.dataset.route === r.tab));
        window.scrollTo(0, 0);
        r.handler(m);
        return;
      }
    }
    location.hash = "#/catalogo";
  }

  window.addEventListener("hashchange", resolve);
  window.addEventListener("DOMContentLoaded", resolve);
})();
