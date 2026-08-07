// page_compras.js — fluxo de compra em tela única (NFC).
// Etapas: 1 Lista ➔ 2 Cotando ➔ 3 Comparando ➔ 4 Pedido Gerado.
const PageCompras = (() => {
  const S = { etapa: 1, cotacaoId: null, logica: "fracionado", draft: null };
  const KEY_DRAFT = "compras_draft";
  const KEY_COT = "compras_cotacao";

  // ------------------------------------------------------------------ helpers
  function esc(s) { return UI.escapeHtml(s == null ? "" : s); }
  function salvar() {
    sessionStorage.setItem(KEY_DRAFT, JSON.stringify(S.draft || {}));
    if (S.cotacaoId) sessionStorage.setItem(KEY_COT, String(S.cotacaoId));
  }
  function novoDraft() {
    return { apelido: "", comprador: "", data_limite: "", agrupar: false,
             itens: [], fornecedores: [] };
  }

  const ETAPAS = [
    { n: 1, nome: "Lista" },
    { n: 2, nome: "Cotando" },
    { n: 3, nome: "Comparando" },
    { n: 4, nome: "Pedido Gerado" },
  ];

  function stepper() {
    return '<div class="cpr-stepper">' + ETAPAS.map((e) =>
      `<div class="cpr-step${e.n === S.etapa ? " is-cur" : ""}${e.n < S.etapa ? " is-done" : ""}">
         <span class="cpr-num">${e.n}</span><span class="cpr-nome">${e.nome}</span>
       </div>`).join('<span class="cpr-link"></span>') +
      `<span class="cpr-status cpr-status-${S.etapa}"></span></div>`;
  }

  function barra(msg) {
    return `<div class="cpr-empty"><div class="cpr-spin"></div><p>${esc(msg)}</p></div>`;
  }

  // ------------------------------------------------------------------ render
  function render($app) {
    $app.innerHTML = `
      <div class="page-head">
        <div><h1 class="page-title">Comprar</h1>
        <p class="page-sub">Monte a lista, cote com os fornecedores e gere o pedido em uma tela só.</p></div>
        <button class="btn btn--ghost" id="cprNova">＋ Nova compra</button>
      </div>
      <div id="cprStepper"></div>
      <div id="cprBody"></div>`;
    $app.querySelector("#cprNova").addEventListener("click", () => {
      sessionStorage.removeItem(KEY_COT); S.cotacaoId = null; S.draft = novoDraft(); salvar();
      S.etapa = 1; desenhar($app);
    });
    init($app);
  }

  async function init($app) {
    S.draft = null;
    try { S.draft = JSON.parse(sessionStorage.getItem(KEY_DRAFT) || "null") || novoDraft(); }
    catch (e) { S.draft = novoDraft(); }
    const stored = sessionStorage.getItem(KEY_COT);
    if (stored) {
      S.cotacaoId = Number(stored);
      S.draft = novoDraft();
      await resume($app);
      return;
    }
    S.etapa = 1;
    desenhar($app);
  }

  // Resume com base no status da cotação já disparada.
  async function resume($app) {
    try {
      const m = await Api.compararCotacao(S.cotacaoId);
      const status = m.cotacao.status;
      if (status === "finalizada") S.etapa = 4;
      else if (status === "analise") S.etapa = 3;
      else S.etapa = 3; // pendente mas já enviada: ver matriz
      desenhar($app);
    } catch (e) {
      sessionStorage.removeItem(KEY_COT); S.cotacaoId = null;
      S.etapa = 1; desenhar($app);
    }
  }

  function desenhar($app) {
    $app.querySelector("#cprStepper").innerHTML = stepper();
    const body = $app.querySelector("#cprBody");
    const fns = { 1: etapaLista, 2: etapaCotando, 3: etapaComparando, 4: etapaPedidos };
    fns[S.etapa](body);
  }

  function setEtapa($app, n) { S.etapa = n; desenhar($app); window.scrollTo(0, 0); }

  // =================================================================== ETAPA 1
  async function etapaLista(body) {
    body.innerHTML = `
      <div class="cpr-grid">
        <div class="cpr-panel cpr-buscar">
          <h3 class="cpr-titulo">Buscar produtos</h3>
          <div class="cpr-pesq">
            <input id="cprQ" type="text" placeholder="Nome, código, EAN ou grupo…">
            <select id="cprCat"><option value="">Todos os grupos</option></select>
          </div>
          <div class="cpr-opcoes">
            <label class="cpr-check"><input type="checkbox" id="cprAgrupar"
              ${S.draft.agrupar ? "checked" : ""}> Não misturar grupos de produtos</label>
          </div>
          <div id="cprResult" class="cpr-result">${barra("Digite para buscar")}</div>
        </div>
        <div class="cpr-panel cpr-minha">
          <h3 class="cpr-titulo">Minha lista <span id="cprNItens" class="cpr-badge">0</span></h3>
          <div class="cpr-dados">
            <input id="cprApelido" type="text" placeholder="Apelido amigável (ex.: Parafusos Agosto)"
              value="${esc(S.draft.apelido)}">
            <div class="cpr-dados-fila">
              <input id="cprData" type="date" value="${esc(S.draft.data_limite)}">
              <span class="cpr-rot">Retorno até</span>
            </div>
          </div>
          <div id="cprLista" class="cpr-lista"></div>
          <div class="cpr-lista-foot">
            <button class="btn btn--accent" id="cprProx1">Continuar ➔ Cotação</button>
          </div>
        </div>
      </div>`;
    await preencherCategorias(body);
    vincularBusca(body);
    desenharLista(body);
  }

  async function preencherCategorias(body) {
    try {
      const cats = await Api.listarCategorias();
      const sel = body.querySelector("#cprCat");
      (cats || []).forEach((c) => sel.insertAdjacentHTML("beforeend",
        `<option value="${esc(c.nome)}">${esc(c.nome)}</option>`));
    } catch (e) {}
  }

  function vincularBusca(body) {
    const q = body.querySelector("#cprQ");
    const cat = body.querySelector("#cprCat");
    let timer = null;
    function buscar() {
      clearTimeout(timer);
      timer = setTimeout(() => {
        Api.listarProdutos({ q: q.value.trim(), categoria: cat.value, limit: 12, agrupado: 1 })
          .then((r) => desenharResultado(body, r.items || []))
          .catch((e) => { body.querySelector("#cprResult").innerHTML = `<p class="cpr-erro">${esc(e.message)}</p>`; });
      }, 300);
    }
    q.addEventListener("input", buscar);
    cat.addEventListener("change", buscar);
    body.querySelector("#cprAgrupar").addEventListener("change", (e) => {
      S.draft.agrupar = e.target.checked; salvar();
    });
  }

  function gpFamilia(itens) {
    const it = itens[0];
    return it ? (it.category || "") : "";
  }

  function desenharResultado(body, itens) {
    const box = body.querySelector("#cprResult");
    if (!itens.length) { box.innerHTML = `<p class="cpr-vazio">Nenhum produto encontrado.</p>`; return; }
    box.innerHTML = itens.map((p) => {
      const vid = (p.group && p.variants && p.variants[0]) ? p.variants[0].id : p.id;
      return `
      <div class="cpr-card">
        <img src="${esc(p.imagem_url || "")}" onerror="this.style.visibility=&#39;hidden&#39;">
        <div class="cpr-card-info">
          <div class="cpr-card-nome">${esc(p.name)}</div>
          <div class="cpr-card-meta">${esc(p.sku || "")}${p.brand ? " · " + esc(p.brand) : ""}${p.category ? " · " + esc(p.category) : ""}</div>
          <div class="cpr-card-preco">${UI.fmtMoney(p.group ? p.price_min : p.price)}</div>
        </div>
        <button class="btn btn--sm btn--accent" data-add="${vid}">Adicionar</button>
      </div>`;
    }).join("");
    box.querySelectorAll("[data-add]").forEach((b) =>
      b.addEventListener("click", () => adicionar(body, Number(b.dataset.add))));
  }

  function adicionar(body, produtoId) {
    // precisa do produto para categoria; recupera do resultado atual
    const box = body.querySelector("#cprResult");
    const card = box.querySelector(`[data-add="${produtoId}"]`);
    const nome = card ? card.closest(".cpr-card").querySelector(".cpr-card-nome").textContent.trim() : "";
    let exist = S.draft.itens.find((i) => i.produto_id === produtoId);
    if (exist) { exist.quantidade += 1; }
    else {
      const cat = card ? catDe(card) : "";
      if (S.draft.agrupar && S.draft.itens.length && cat && gpFamilia(S.draft.itens) !== cat) {
        UI.toast("Grupo diferente: ative a opção de não misturar ou remova o item.", "error");
        return;
      }
      S.draft.itens.push({ produto_id: produtoId, quantidade: 1, name: nome, category: cat });
    }
    salvar(); desenharLista(body);
  }

  function catDe(card) {
    const m = card.querySelector(".cpr-card-meta");
    const t = m ? m.textContent.split(" · ") : [];
    return t.length ? t[t.length - 1] : "";
  }

  function desenharLista(body) {
    const box = body.querySelector("#cprLista");
    body.querySelector("#cprNItens").textContent = S.draft.itens.length;
    if (!S.draft.itens.length) { box.innerHTML = `<p class="cpr-vazio">Nenhum item na lista.<br>Use a busca ao lado e clique em "Adicionar".</p>`; return; }
    box.innerHTML = S.draft.itens.map((it, idx) => `
      <div class="cpr-linha" data-idx="${idx}">
        <span class="cpr-linha-nome">${esc(it.name || "#" + it.produto_id)}</span>
        <input class="cpr-qtd" type="number" min="1" step="1" value="${it.quantidade}" data-idx="${idx}">
        <button class="btn btn--sm btn--ghost cpr-rm" data-idx="${idx}">✕</button>
      </div>`).join("");
    // navegação por Enter/Tab para a próxima linha
    box.querySelectorAll(".cpr-qtd").forEach((inp) => {
      inp.addEventListener("input", () => {
        const it = S.draft.itens[Number(inp.dataset.idx)];
        it.quantidade = Math.max(1, Number(inp.value) || 1); salvar();
      });
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === "Tab") {
          const next = box.querySelector(`.cpr-qtd[data-idx="${Number(inp.dataset.idx) + 1}"]`);
          if (next) { e.preventDefault(); next.focus(); next.select(); }
        }
      });
    });
    box.querySelectorAll(".cpr-rm").forEach((b) =>
      b.addEventListener("click", () => {
        S.draft.itens.splice(Number(b.dataset.idx), 1); salvar(); desenharLista(body);
      }));
    body.querySelector("#cprApelido").addEventListener("input", (e) => { S.draft.apelido = e.target.value; salvar(); });
    body.querySelector("#cprData").addEventListener("change", (e) => { S.draft.data_limite = e.target.value; salvar(); });
    const btn = body.querySelector("#cprProx1");
    if (btn && !btn.dataset.bound) {
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        if (!S.draft.itens.length) { UI.toast("Adicione pelo menos 1 produto.", "error"); return; }
        S.etapa = 2; desenhar(body.closest("#app"));
      });
    }
  }

  // =================================================================== ETAPA 2
  async function etapaCotando(body) {
    body.innerHTML = `
      <div class="cpr-grid">
        <div class="cpr-panel">
          <div class="cpr-footer-apnel"><h3 class="cpr-titulo">Sua lista está pronta</h3>
            <p class="cpr-sub">${esc(S.draft.itens.length)} itens ${S.draft.apelido ? "· “" + esc(S.draft.apelido) + "”" : ""}</p></div>
          <div id="cprMiniLista" class="cpr-minilista"></div>
        </div>
        <div class="cpr-panel">
          <h3 class="cpr-titulo">Convide fornecedores</h3>
          <div id="cprForn" class="cpr-forn"></div>
          <h4 class="cpr-subtitulo">Cadastro rápido</h4>
          <div class="cpr-express">
            <input id="fxNome" placeholder="Nome do fornecedor">
            <input id="fxWhats" placeholder="WhatsApp (só números)">
            <input id="fxEmail" placeholder="E-mail (opcional)">
            <button class="btn" id="fxAdd">Adicionar</button>
          </div>
          <div class="cpr-lista-foot">
            <button class="btn btn--accent btn--wa" id="cprDisparar">Disparar Cotação ➔</button>
          </div>
        </div>
      </div>`;
    desenharMiniLista(body);
    await desenharFornecedores(body);
    vincularExpress(body);
    body.querySelector("#cprDisparar").addEventListener("click", () => disparar(body));
  }

  function desenharMiniLista(body) {
    const box = body.querySelector("#cprMiniLista");
    box.innerHTML = S.draft.itens.map((it) =>
      `<div class="cpr-mini"><span>${esc(it.name || "#" + it.produto_id)}</span><b>${it.quantidade}</b></div>`).join("");
  }

  async function desenharFornecedores(body) {
    let fornecedores = [];
    try { fornecedores = await Api.listarFornecedores(true); } catch (e) {}
    S.draft.fornecedores = S.draft.fornecedores.filter((f) => f.id);
    const box = body.querySelector("#cprForn");
    box.innerHTML = fornecedores.map((f) => {
      const sel = S.draft.fornecedores.some((x) => x.id === f.id);
      return `<label class="cpr-linha cpr-frow">
        <input type="checkbox" data-fid="${f.id}" ${sel ? "checked" : ""}>
        <span>${esc(f.nome)}</span>
        <small>${esc(f.whatsapp || (f.email ? "e-mail" : "sem contato"))}</small>
      </label>`;
    }).join("") || `<p class="cpr-vazio">Nenhum fornecedor cadastrado.</p>`;
    box.querySelectorAll("input[type=checkbox]").forEach((c) =>
      c.addEventListener("change", () => {
        const fid = Number(c.dataset.fid);
        if (c.checked) S.draft.fornecedores.push({ id: fid });
        else S.draft.fornecedores = S.draft.fornecedores.filter((x) => x.id !== fid);
        salvar();
      }));
  }

  function vincularExpress(body) {
    const add = body.querySelector("#fxAdd");
    add.addEventListener("click", () => {
      const nome = body.querySelector("#fxNome").value.trim();
      if (!nome) { UI.toast("Informe o nome do fornecedor.", "error"); return; }
      S.draft.fornecedores.push({
        id: null,
        nome,
        whatsapp: body.querySelector("#fxWhats").value.trim(),
        email: body.querySelector("#fxEmail").value.trim(),
      });
      body.querySelector("#fxNome").value = "";
      body.querySelector("#fxWhats").value = "";
      body.querySelector("#fxEmail").value = "";
      desenharFornecedores(body);
      UI.toast("Fornecedor rápido adicionado à cotação.");
    });
  }

  async function disparar(body) {
    if (!S.draft.fornecedores.length) { UI.toast("Convide pelo menos 1 fornecedor.", "error"); return; }
    const btn = body.querySelector("#cprDisparar");
    btn.disabled = true; btn.classList.add("is-loading"); btn.innerHTML = '<span class="spinner"></span> Enviando…';
    const payload = {
      apelido: S.draft.apelido,
      comprador: S.draft.comprador || "Loja",
      data_limite: S.draft.data_limite,
      itens: S.draft.itens.map((i) => ({ produto_id: i.produto_id, quantidade: i.quantidade })),
      fornecedores: S.draft.fornecedores.map((f) =>
        f.id ? { fornecedor_id: f.id } : { nome: f.nome, whatsapp: f.whatsapp, email: f.email }),
    };
    try {
      const r = await Api.criarCotacaoCompras(payload);
      S.cotacaoId = r.id;
      S.draft.fornecedores = [];
      sessionStorage.setItem(KEY_COT, String(r.id));
      salvar();
      await mostrarLinks(body, r.invites || []);
    } catch (e) {
      btn.disabled = false; btn.classList.remove("is-loading");
      btn.innerHTML = "Disparar Cotação ➔";
      UI.toast(e.message, "error");
    }
  }

  async function mostrarLinks(body, invites) {
    const box = body.querySelector("#cprBody") || body.closest("#app").querySelector("#cprBody");
    box.innerHTML = `
      <div class="cpr-panel cpr-links">
        <h3 class="cpr-titulo">Cotações disparadas! Envie para cada fornecedor</h3>
        <p class="cpr-sub">Toque no WhatsApp (verde) para abrir a conversa pronta, ou copie o link.</p>
        <div id="cprLinks"></div>
        <div class="cpr-lista-foot" style="justify-content:space-between">
          <button class="btn" id="cprVoltarLista">← Editar lista</button>
          <button class="btn btn--accent" id="cprIrComparar">Ir para Comparação ➔</button>
        </div>
      </div>`;
    const links = box.querySelector("#cprLinks");
    links.innerHTML = invites.map((inv) => `
      <div class="cpr-linkcard">
        <div><b>${esc(inv.nome)}</b><span class="cpr-lk-status">${inv.status === "respondido" ? "✓ respondeu" : "pendente"}</span></div>
        <div class="cpr-lk-acoes">
          ${inv.whatsapp_url
            ? `<a class="btn btn--wa" target="_blank" rel="noopener" href="${esc(inv.whatsapp_url)}">WhatsApp</a>` : ""}
          ${inv.mailto_url ? `<a class="btn" href="${esc(inv.mailto_url)}">E-mail</a>` : ""}
          <button class="btn" data-copiar="${esc(inv.link)}">Copiar link</button>
        </div>
      </div>`).join("");
    links.querySelectorAll("[data-copiar]").forEach((b) =>
      b.addEventListener("click", (e) => {
        const url = e.currentTarget.dataset.copiar;
        navigator.clipboard.writeText(url).then(() => UI.toast("Link copiado!"));
      }));
    box.querySelector("#cprVoltarLista").addEventListener("click", () => { S.etapa = 2; desenhar(body.closest("#app")); });
    box.querySelector("#cprIrComparar").addEventListener("click", () => { S.etapa = 3; desenhar(body.closest("#app")); });
  }

  // =================================================================== ETAPA 3
  async function etapaComparando(body) {
    body.innerHTML = `<div class="cpr-panel">${barra("Aguardando respostas dos fornecedores…")}</div>`;
    try {
      const m = await Api.compararCotacao(S.cotacaoId);
      if ((m.cotacao.status !== "analise" && m.cotacao.status !== "finalizada") &&
          !m.fornecedores.some((f) => f.status === "respondido")) {
        body.innerHTML = `
          <div class="cpr-panel cpr-wait">
            <div class="cpr-spin"></div>
            <h3 class="cpr-titulo">Cotação disparada — aguardando respostas</h3>
            <p class="cpr-sub">Quando os fornecedores responderem (ou você apertar o botão), a matriz aparece aqui.</p>
            <button class="btn btn--accent" id="cprRecarregar">Atualizar respostas</button>
          </div>`;
        body.querySelector("#cprRecarregar").addEventListener("click", () => etapaComparando(body));
        return;
      }
      desenharMatriz(body, m);
    } catch (e) {
      body.innerHTML = `<p class="cpr-erro">${esc(e.message)}</p>`;
    }
  }

  function desenharMatriz(body, m) {
    const fornecedores = m.fornecedores;
    const central = m.centralizado;
    const vencedorCentral = central ? central.fornecedor_id : null;
    body.innerHTML = `
      <div class="cpr-panel">
        <div class="cpr-matriz-head">
          <h3 class="cpr-titulo">Comparar propostas ${esc(m.cotacao.titulo ? "— “" + m.cotacao.titulo + "”" : "")}</h3>
          <div class="cpr-logica">
            <button class="btn${m.logica === "fracionado" ? " btn--accent" : ""}" data-logica="fracionado">Melhor preço por item</button>
            <button class="btn${m.logica === "centralizado" ? " btn--accent" : ""}" data-logica="centralizado">Melhor preço por lote</button>
          </div>
        </div>
        ${central ? `<p class="cpr-central">Opção de lote: <b>${esc(central.nome)}</b> — total ${UI.fmtMoney(central.total)}</p>` :
          `<p class="cpr-central cpr-central-none">Nenhum fornecedor precificou todos os itens para a opção de lote.</p>`}
        <div class="cpr-ttrowe">
          <div class="cpr-tabwrap">
            <table class="cpr-matriz ${m.logica}">
              <thead><tr><th class="cpr-col-prod">Produto</th>
                ${fornecedores.map((f) => `<th>${esc(f.nome)}${f.status === "respondido" ? "" : '<span class="cpr-noresp">—</span>'}</th>`).join("")}
              </tr></thead>
              <tbody>${m.itens.map((it) => linhaMatriz(it, fornecedores, m.logica, vencedorCentral)).join("")}</tbody>
            </table>
          </div>
        </div>
        <div class="cpr-lista-foot" style="justify-content:space-between">
          <button class="btn" id="cprRecarregar2">↻ Atualizar respostas</button>
          <button class="btn btn--accent" id="cprGerarPedidos">Gerar Pedidos ➔</button>
        </div>
      </div>`;
    body.querySelectorAll("[data-logica]").forEach((b) =>
      b.addEventListener("click", () => {
        m.logica = b.dataset.logica;
        desenharMatriz(body, m);
      }));
    body.querySelector("#cprRecarregar2").addEventListener("click", () => etapaComparando(body));
    body.querySelector("#cprGerarPedidos").addEventListener("click", async () => {
      const btn = body.querySelector("#cprGerarPedidos");
      btn.disabled = true; btn.classList.add("is-loading"); btn.innerHTML = '<span class="spinner"></span> Gerando…';
      try {
        await Api.gerarPedidos(S.cotacaoId, m.logica);
        S.etapa = 4; desenhar(body.closest("#app"));
      } catch (e) { btn.disabled = false; btn.classList.remove("is-loading"); UI.toast(e.message, "error"); }
    });
  }

  function linhaMatriz(it, fornecedores, logica, vencedorCentral) {
    const cells = fornecedores.map((f) => {
      const pr = it.precos[String(f.fornecedor_id)];
      if (!pr) return `<td><span class="cpr-x">—</span></td>`;
      const venceu = logica === "centralizado"
        ? (vencedorCentral === f.fornecedor_id && pr.disponivel && pr.preco_liquido > 0)
        : (it.melhor_id === f.fornecedor_id);
      const cls = venceu ? " cpr-melhor" : "";
      return `<td class="cpr-prece${cls}">${pr.disponivel ? "" : "<span class='cpr-esgot'>s/ estoque</span>"}
        <b>${UI.fmtMoney(pr.preco_liquido)}</b>
        <small>${pr.desconto ? "desconto " + pr.desconto + "%" : ""}${pr.prazo ? " · " + pr.prazo + "d" : ""}</small></td>`;
    }).join("");
    return `<tr><td class="cpr-col-prod"><b>${esc(it.name)}</b><small>qtd ${it.quantidade}</small></td>${cells}</tr>`;
  }

  // =================================================================== ETAPA 4
  async function etapaPedidos(body) {
    body.innerHTML = `<div class="cpr-panel">${barra("Gerando pedidos…")}</div>`;
    try {
      const pedidos = await Api.listarPedidos();
      const meus = pedidos.filter((p) => (S.cotacaoId == null || true));
      body.innerHTML = `
        <div class="cpr-panel">
          <h3 class="cpr-titulo">Pedidos gerados — envie para os fornecedores</h3>
          <p class="cpr-sub">Cada pedido consolida os itens vencedores por fornecedor.</p>
          <div id="cprPedidos"></div>
        </div>`;
      const box = body.querySelector("#cprPedidos");
      if (!meus.length) { box.innerHTML = `<p class="cpr-vazio">Nenhum pedido ainda.</p>`; return; }
      box.innerHTML = meus.map((p) => `
        <div class="cpr-pedido">
          <div class="cpr-pedido-top">
            <div><b>Pedido ${esc(p.numero)}</b><span class="cpr-lk-status">${esc(p.fornecedor)}</span></div>
            <div class="cpr-pedido-total">${UI.fmtMoney(p.total)}</div>
          </div>
          <div class="cpr-pedido-acao">
            <a class="btn" target="_blank" href="/compras/pedidos/${esc(p.id)}/imprimir">PDF</a>
            ${p.whatsapp ? `<a class="btn btn--wa" target="_blank" rel="noopener"
                href="https://wa.me/${esc(p.whatsapp)}?text=${encodeURIComponent("Olá " + p.fornecedor + ", segue nosso pedido de compras número " + p.numero + " referente à cotação aprovada. Aguardamos o faturamento e entrega!")}">WhatsApp</a>` : ""}
          </div>
        </div>`).join("");
    } catch (e) {
      body.innerHTML = `<p class="cpr-erro">${esc(e.message)}</p>`;
    }
  }

  // ------------------------------------------------------------------ export
  return { render };
})();