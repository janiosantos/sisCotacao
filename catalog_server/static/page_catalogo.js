// page_catalogo.js — catálogo (filtros + grid) e seleção de variações por matriz.
const PageCatalogo = (() => {
  let categorias = {};
  let filters = { categoria: "", subcategoria: "", q: "" };
  let items = [];
  let total = 0;
  let page = 1;
  let loading = false;
  let draft = Cart.load();
  let currentApp = null;
  let agrupado = true;

  const PAGE = 60;

  // ---------------- matriz 2D de variações (utilidade) ----------------

  function naturalCompare(a, b) {
    const re = /(\d+)|(\D+)/g;
    const aParts = String(a).match(re) || [];
    const bParts = String(b).match(re) || [];
    const n = Math.max(aParts.length, bParts.length);
    for (let i = 0; i < n; i++) {
      const pa = aParts[i];
      const pb = bParts[i];
      if (pa == null) return -1;
      if (pb == null) return 1;
      const na = /^\d+$/.test(pa);
      const nb = /^\d+$/.test(pb);
      if (na && nb) {
        const d = Number(pa) - Number(pb);
        if (d) return d;
      } else {
        const d = pa.localeCompare(pb, "pt");
        if (d) return d;
      }
    }
    return 0;
  }

  function orderedOptions(attr, vset) {
    const seen = new Set();
    const vals = [];
    (attr.options || []).forEach((o) => {
      const key = String(o);
      if (!seen.has(key)) { seen.add(key); vals.push(o); }
    });
    vset.forEach((v) => {
      const val = v.attrs ? v.attrs[String(attr.id)] : undefined;
      if (val == null) return;
      const key = String(val);
      if (!seen.has(key)) { seen.add(key); vals.push(val); }
    });
    return vals.sort(naturalCompare);
  }

  /** Agrupa a lista linear de variações em uma matriz 2D (linhas x colunas).
   *  Linhas = atributo dimensional/técnico; colunas = atributo secundário/visual.
   *  Retorna { rowAttr, colAttr, rows: [{value, tip, cells:[{colValue, variant}]}] }.
   */
  function buildVariationMatrix(variations, meta) {
    const attrs = (meta && meta.attrs) || [];
    const vset = variations || [];
    const usable = attrs.filter((a) => vset.some((v) => v.attrs && v.attrs[String(a.id)] != null));
    const DIM = /bitola|di[âa]metro|tamanho|medida|capacidade|pot[eê]ncia|tens[aã]o|voltagem|corrente|amperagem|comprimento|volume|peso|quantidade|rolo|embalagem|mm|w\b|litros|kg|metro|pol/i;

    let row = null;
    let col = null;
    if (usable.length === 1) {
      row = usable[0];
    } else if (usable.length >= 2) {
      const dims = usable.filter((a) => DIM.test(a.label || ""));
      row = dims[0] || usable[0];
      col = usable.find((a) => a.id !== row.id) || null;
    }
    if (!row) {
      return { rowAttr: null, colAttr: null, rows: [] };
    }

    const rowValues = orderedOptions(row, vset);
    const colValues = col ? orderedOptions(col, vset) : ["_"];

    const cellMap = {};
    vset.forEach((v) => {
      const rv = v.attrs ? v.attrs[String(row.id)] : undefined;
      if (rv == null) return;
      const cv = col ? String(v.attrs[String(col.id)] ?? "_") : "_";
      const keyR = String(rv);
      cellMap[keyR] = cellMap[keyR] || {};
      const prev = cellMap[keyR][cv];
      if (!prev || (v.price != null && (prev.price == null || v.price < prev.price))) {
        cellMap[keyR][cv] = v;
      }
    });

    const rows = rowValues.map((value) => ({
      value,
      tip: tipValor(row.label || "", value),
      cells: colValues.map((cv) => ({
        colValue: cv === "_" ? null : cv,
        variant: cellMap[value] && cellMap[value][cv] ? cellMap[value][cv] : null,
      })),
    }));

    return { rowAttr: row, colAttr: col, rows };
  }

  // ---------------- tooltips educativos ----------------

  const ATTR_TIPS = {
    "bitola": "Bitola = seção do condutor. Quanto maior, maior a corrente que o cabo suporta.",
    "diametro": "Diâmetro da peça (mm ou polegadas).",
    "tamanho": "Tamanho / medida da peça.",
    "medida": "Medida do produto.",
    "tensao": "Tensão de operação. Confira a instalação: 127V ou 220V.",
    "voltagem": "Tensão de operação (127V ou 220V).",
    "potencia": "Consumo elétrico em watts. Mais watts = mais potência/brilho.",
    "temperatura de cor": "Tom da luz: fria (trabalho), neutra (áreas gerais), quente (conforto).",
    "cor": "Cor da peça. Escolha a desejada.",
    "capacidade": "Capacidade que o produto comporta (volume/massa).",
    "embalagem": "Forma de venda (rolo inteiro ou avulso, por exemplo).",
  };
  const TIPS_VALORES = {
    "bitola": {
      "1,5": "Ideal para iluminação",
      "2,5": "Tomadas de uso geral",
      "4": "Chuveiros até 5.500W",
      "6": "Chuveiros elétricos potentes",
      "10": "Torneiras elétricas / centrais",
    },
    "tensao": {
      "127v": "Padrão residencial (110–127V)",
      "110v": "Padrão residencial (110–127V)",
      "220v": "Comum no interior do país (200–240V)",
      "220": "Comum no interior (200–240V)",
    },
    "potencia": {
      "9w": "Menor consumo — áreas de convivência",
      "12w": "Mais brilho — áreas de trabalho",
    },
  };

  function normTip(s) {
    return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function tipValor(attrLabel, valor) {
    const al = normTip(attrLabel);
    const vk = Object.keys(TIPS_VALORES).find((k) => al.includes(k));
    if (vk) {
      const v = normTip(valor);
      const t = Object.keys(TIPS_VALORES[vk]).find((k) => v.includes(k) || k.includes(v));
      if (t) return TIPS_VALORES[vk][t];
    }
    const g = Object.keys(ATTR_TIPS).find((k) => al.includes(k));
    return g ? ATTR_TIPS[g] : "Especifique a característica para montar o pedido.";
  }

  // ---------------- estado do carrinho ----------------

  function detFromItem(p) {
    return {
      name: p.name || "",
      spec: p.spec || "",
      brand: p.brand || "",
      price: p.price || 0,
      imagem_url: p.imagem_url || "",
    };
  }

  async function render($app) {
    currentApp = $app;
    $app.innerHTML = `<div class="loading">Carregando catálogo…</div>`;
    try {
      categorias = await Api.listarCategorias();
    } catch (e) {
      categorias = {};
    }

    $app.innerHTML = `
      <div class="catalog-layout">
        <div class="catalog-main">
          <div class="page-head">
            <div>
              <h1 class="page-title">Catálogo</h1>
              <p class="page-sub">Consulte produtos e selecione quantidades para montar uma cotação.</p>
            </div>
          </div>

          <div class="toolbar">
            <div class="field" style="min-width:240px;flex:1;">
              <label>Buscar</label>
              <input id="fSearch" type="text" placeholder="Nome, código, marca…" autocomplete="off">
              <p class="search-hint" id="searchHint">Digite ao menos 3 caracteres para buscar.</p>
            </div>
            <div class="field">
              <label>Categoria</label>
              <select id="fCategoria"><option value="">Todas</option></select>
            </div>
            <div class="field">
              <label>Subcategoria</label>
              <select id="fSubcategoria"><option value="">Todas</option></select>
            </div>
            <button class="btn btn--ghost" id="btnLimpar">Limpar filtros</button>
            <button class="btn" id="btnModo"></button>
            <span class="result-count" id="resultCount"></span>
          </div>

          <div id="grid" class="product-grid"></div>
          <div class="load-more" id="paginacao"></div>
        </div>
        <aside id="cartSidebar" class="cart-sidebar-slot"></aside>
      </div>
    `;
    Cart.mountSidebar($app.querySelector("#cartSidebar"));

    const $categoria = $app.querySelector("#fCategoria");
    for (const cat of Object.keys(categorias).sort()) {
      $categoria.insertAdjacentHTML("beforeend", `<option value="${UI.escapeHtml(cat)}">${UI.escapeHtml(UI.titleCase(cat))}</option>`);
    }
    updateSubcategoryOptions($app);

    const $search = $app.querySelector("#fSearch");
    const $hint = $app.querySelector("#searchHint");
    $search.addEventListener("input", debounce((e) => {
      const v = e.target.value.trim();
      if (v.length > 0 && v.length < 3) {
        $hint.style.display = "block";
        if (filters.q !== "") { filters.q = ""; loadProducts($app, true); }
        return;
      }
      $hint.style.display = "none";
      filters.q = v;
      loadProducts($app, true);
    }, 300));
    $categoria.addEventListener("change", (e) => {
      filters.categoria = e.target.value;
      filters.subcategoria = "";
      updateSubcategoryOptions($app);
      loadProducts($app, true);
    });
    $app.querySelector("#fSubcategoria").addEventListener("change", (e) => {
      filters.subcategoria = e.target.value;
      loadProducts($app, true);
    });
    $app.querySelector("#btnLimpar").addEventListener("click", () => {
      filters = { categoria: "", subcategoria: "", q: "" };
      $app.querySelector("#fSearch").value = "";
      $categoria.value = "";
      updateSubcategoryOptions($app);
      loadProducts($app, true);
    });
    const $modo = $app.querySelector("#btnModo");
    const updateModoLabel = () => {
      $modo.textContent = agrupado ? "Ver todas as opções" : "Ver por produto";
      $modo.title = agrupado
        ? "Mostra cada cor, tamanho ou marca separadamente, com seu preço."
        : "Agrupa cor, tamanho e marca do mesmo produto em um só card.";
    };
    updateModoLabel();
    $modo.addEventListener("click", () => {
      agrupado = !agrupado;
      updateModoLabel();
      loadProducts($app, true);
    });

    renderDraftBar($app);
    loadProducts($app, true);
  }

  function updateSubcategoryOptions($app) {
    const $sub = $app.querySelector("#fSubcategoria");
    $sub.innerHTML = '<option value="">Todas</option>';
    const subs = filters.categoria
      ? (categorias[filters.categoria] || [])
      : [...new Set(Object.values(categorias).flat())];
    for (const s of subs.slice().sort()) {
      $sub.insertAdjacentHTML("beforeend", `<option value="${UI.escapeHtml(s)}">${UI.escapeHtml(UI.titleCase(s))}</option>`);
    }
  }

  async function loadProducts($app, reset) {
    if (loading) return;
    if (reset) page = 1;
    loading = true;
    const $grid = $app.querySelector("#grid");
    try {
      const res = await Api.listarProdutos({
        categoria: filters.categoria,
        subcategoria: filters.subcategoria,
        q: filters.q,
        offset: (page - 1) * PAGE,
        limit: PAGE,
        agrupado: agrupado ? 1 : 0,
      });
      items = res.items;
      total = res.total;
      renderGrid($app);
      renderPaginacao($app);
    } catch (e) {
      UI.toast("Erro ao carregar catálogo: " + e.message, "error");
    } finally {
      loading = false;
    }
  }

  function renderPaginacao($app) {
    const $wrap = $app.querySelector("#paginacao");
    const paginas = Math.max(1, Math.ceil(total / PAGE));
    if (paginas <= 1) { $wrap.innerHTML = ""; return; }
    const atual = Math.min(Math.max(1, page), paginas);
    const botoes = [];
    const addBtn = (label, p, opts = {}) => {
      botoes.push(`<button class="btn btn--sm pg-btn ${opts.active ? "btn--accent" : ""}" data-page="${p}" ${opts.disabled ? "disabled" : ""}>${label}</button>`);
    };
    addBtn("«", atual - 1, { disabled: atual <= 1 });
    const inicio = Math.max(1, atual - 3);
    const fim = Math.min(paginas, atual + 3);
    if (inicio > 1) {
      addBtn("1", 1);
      if (inicio > 2) botoes.push('<span class="pg-ellipsis">…</span>');
    }
    for (let p = inicio; p <= fim; p++) addBtn(String(p), p, { active: p === atual });
    if (fim < paginas) {
      if (fim < paginas - 1) botoes.push('<span class="pg-ellipsis">…</span>');
      addBtn(String(paginas), paginas);
    }
    addBtn("»", atual + 1, { disabled: atual >= paginas });
    $wrap.innerHTML = `
      <div class="pagination">
        <span class="pg-info">Página ${atual} de ${paginas} · ${total} produto(s)</span>
        <div class="pg-btns">${botoes.join("")}</div>
      </div>`;
    $wrap.querySelectorAll("[data-page]").forEach((b) => {
      if (b.disabled) return;
      b.onclick = () => { page = Number(b.dataset.page); loadProducts($app, false); };
    });
  }

  function renderGrid($app) {
    $app.querySelector("#resultCount").textContent = `${total} produto(s)`;
    const $grid = $app.querySelector("#grid");
    if (items.length === 0) {
      $grid.innerHTML = `<div class="empty-box" style="grid-column:1/-1;"><p>Nada encontrado</p><p>Tente outro termo de busca ou categoria.</p></div>`;
      return;
    }
    $grid.innerHTML = items.map(cardHtml).join("");
    $grid.querySelectorAll(".p-card").forEach((card) => {
      if (card.dataset.group) {
        const p = items.find((x) => x.group && x.id === Number(card.dataset.group));
        const abrir = () => abrirModalVariante(p);
        card.querySelector(".p-photo").addEventListener("click", abrir);
        card.querySelector(".p-pick").addEventListener("click", abrir);
        return;
      }
      const produtoId = Number(card.dataset.id);
      const item = items.find((x) => x.id === produtoId);
      const det = item ? detFromItem(item) : undefined;
      card.querySelector(".p-minus").addEventListener("click", () => setQty(produtoId, Math.max(0, (draft.itens[produtoId] || 0) - 1), $app, det));
      card.querySelector(".p-plus").addEventListener("click", () => setQty(produtoId, (draft.itens[produtoId] || 0) + 1, $app, det));
      card.querySelector(".p-qty").addEventListener("change", (e) => setQty(produtoId, Math.max(0, parseInt(e.target.value, 10) || 0), $app, det));
      card.querySelector(".p-photo").addEventListener("click", () => abrirModalProduto(produtoId));
    });
  }

  function cardHtml(p) {
    if (p.group) return groupCardHtml(p);
    const qty = draft.itens[p.id] || 0;
    const price = UI.fmtMoney(p.price);
    return `
      <article class="p-card ${qty > 0 ? "is-selected" : ""}" data-id="${p.id}">
        <div class="p-photo">${p.imagem_url ? `<img src="${UI.escapeHtml(p.imagem_url)}" loading="lazy" alt="">` : `<span style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">sem imagem</span>`}</div>
        <div class="p-body">
          <p class="p-code">${UI.escapeHtml(p.sku || "#" + p.id)}</p>
          <p class="p-desc">${UI.escapeHtml(p.name)}</p>
          ${p.spec ? `<p class="p-spec">${UI.escapeHtml(p.spec)}</p>` : ""}
          ${p.brand ? `<p class="p-brand">${UI.escapeHtml(p.brand)}</p>` : ""}
          <div class="p-price-row">
            <p class="p-price">${price}</p>
            ${p.package_label ? `<span class="p-unit-badge">${UI.escapeHtml(p.package_label)}</span>` : ""}
          </div>
          ${qty > 0 ? `<p class="p-in-cart">${qty} no carrinho</p>` : ""}
        </div>
        <div class="p-controls">
          <button class="p-minus" type="button" aria-label="Diminuir quantidade">–</button>
          <input class="p-qty" type="number" min="0" value="${qty}" aria-label="Quantidade">
          <button class="p-plus" type="button" aria-label="Aumentar quantidade">+</button>
        </div>
      </article>`;
  }

  function groupCardHtml(p) {
    const naDraft = p.variants.reduce((s, v) => s + (draft.itens[v.id] || 0), 0);
    const pkgLabel = p.package_label || "";
    const priceLabel = p.price_min !== p.price_max
      ? `a partir de ${UI.fmtMoney(p.price_min)}`
      : UI.fmtMoney(p.price_min);
    return `
      <article class="p-card ${naDraft > 0 ? "is-selected" : ""}" data-group="${p.id}">
        <div class="p-photo">${p.imagem_url ? `<img src="${UI.escapeHtml(p.imagem_url)}" loading="lazy" alt="">` : `<span style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">sem imagem</span>`}</div>
        <div class="p-body">
          <p class="p-code">${pkgLabel ? `<span class="p-badge">${UI.escapeHtml(pkgLabel)}</span>` : ""}${p.variant_count} variações</p>
          <p class="p-desc">${UI.escapeHtml(p.name)}</p>
          <p class="p-price">${priceLabel}</p>
        </div>
        <div class="p-actions">
          <button class="btn btn--accent btn--sm p-pick">${naDraft > 0 ? `${naDraft} no carrinho · ` : ""}Escolher variação</button>
        </div>
      </article>`;
  }

  function setQty(produtoId, qty, $app, det) {
    Cart.setQty(produtoId, qty, det);
    draft = Cart.load();
    if (currentApp) refreshGridSelection(currentApp);
    renderDraftBar($app);
  }

  function renderDraftBar($app) {
    const $bar = $app ? $app.querySelector("#draftBar") : null;
    if (!$bar) return;
    const ids = Object.keys(draft.itens).filter((id) => Number(draft.itens[id]) > 0);
    if (ids.length === 0) {
      $bar.innerHTML = `<span style="color:#B9BDB2;font-size:13px;">Nenhum produto selecionado ainda. Use os controles “+” nos produtos acima.</span>`;
      return;
    }
    const totalQtd = ids.reduce((s, id) => s + draft.itens[id], 0);
    $bar.innerHTML = `
      <span><strong>${ids.length}</strong> itens · <strong>${totalQtd}</strong> unidades no carrinho</span>
      <span class="spacer"></span>
      <button class="btn btn--ghost" id="btnLimparDraft">Limpar carrinho</button>
      <button class="btn btn--accent" id="btnCriarCotacao">Criar cotação →</button>
    `;
    $bar.querySelector("#btnLimparDraft").addEventListener("click", async () => {
      if (!(await UI.confirmDialog("Limpar todos os itens do carrinho atual?"))) return;
      Cart.clear();
      draft = Cart.load();
      renderGrid($app);
      renderDraftBar($app);
    });
    $bar.querySelector("#btnCriarCotacao").addEventListener("click", (e) => Cart.criarCotacao(e.currentTarget));
  }

  async function abrirModalProduto(produtoId) {
    let p;
    try {
      p = await Api.detalharProduto(produtoId);
    } catch (e) {
      UI.toast("Erro ao carregar produto", "error");
      return;
    }
    const imgs = p.image_urls && p.image_urls.length ? p.image_urls : [];
    const mainImg = imgs.length ? imgs[0] : "";
    UI.openModal(
      `<div class="modal-head"><h3>Produto</h3><button class="icon-btn" data-close>×</button></div>
       <div class="prod-gallery">
         <img class="prod-main" id="pMain" src="${UI.escapeHtml(mainImg)}" alt="">
         ${imgs.length > 1 ? `<div class="prod-thumbs">${imgs.map((u, i) => `<img data-src="${UI.escapeHtml(u)}" src="${UI.escapeHtml(u)}" class="${i === 0 ? "is-active" : ""}">`).join("")}</div>` : ""}
       </div>
       <p class="p-code" style="margin:0;">${UI.escapeHtml(p.sku || "#" + p.id)}</p>
       <h3 style="font-family:var(--font-body);text-transform:none;font-size:16px;letter-spacing:0;margin:6px 0 0;">${UI.escapeHtml(p.name)}</h3>
       ${p.brand ? `<div class="prod-meta">Marca: ${UI.escapeHtml(p.brand)}</div>` : ""}
       ${p.color ? `<div class="prod-meta">Cor: ${UI.escapeHtml(p.color)}</div>` : ""}
       <div class="prod-price">${UI.fmtMoney(p.price)}</div>
       ${p.pix_price ? `<div class="prod-meta" style="color:var(--green);font-weight:600;">PIX: ${UI.fmtMoney(p.pix_price)}</div>` : ""}
       ${p.installment ? `<div class="prod-meta">${UI.escapeHtml(p.installment)}</div>` : ""}
       <div class="prod-add">
         <input type="number" id="pQty" value="1" min="1" step="1">
         <button class="btn btn--accent" id="pAdd">Adicionar à cotação</button>
       </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          const $main = modal.querySelector("#pMain");
          modal.querySelectorAll(".prod-thumbs img").forEach((t) => {
            t.addEventListener("click", () => {
              $main.src = t.dataset.src;
              modal.querySelectorAll(".prod-thumbs img").forEach((x) => x.classList.remove("is-active"));
              t.classList.add("is-active");
            });
          });
          modal.querySelector("#pAdd").onclick = () => {
            const qty = Math.max(1, parseInt(modal.querySelector("#pQty").value, 10) || 1);
            Cart.addItem(p.id, qty, {
              name: p.name || "",
              spec: [p.color].filter(Boolean).join(", "),
              brand: p.brand || "",
              price: p.price || 0,
              imagem_url: mainImg || "",
            });
            UI.closeModal();
            UI.toast(`${qty} item(ns) adicionado(s) à sua cotação`, "success");
          };
        },
      }
    );
  }

  async function abrirModalVariante(p) {
    const variants = p.variants || [];
    const brands = (p.brands && p.brands.length) ? p.brands.slice() : [];
    let selBrand = brands.length ? brands[0] : null;
    const qtys = {};
    const allById = {};
    variants.forEach((v) => { allById[v.id] = v; });
    const pkgLabel = p.package_label || "";

    const filtered = () => (selBrand ? variants.filter((v) => (v.brand || "") === selBrand) : variants);

    function melhorPrecoUn(lista) {
      const prices = lista.map((v) => v.price).filter((x) => x != null && x > 0);
      return prices.length ? Math.min(...prices) : null;
    }

    function fornecedorSugerido() {
      const pesos = {};
      Object.entries(qtys).forEach(([id, q]) => {
        if (!q) return;
        const v = allById[id];
        if (!v) return;
        (v.fornecedores || []).forEach((n) => { pesos[n] = (pesos[n] || 0) + q; });
      });
      const best = Object.entries(pesos).sort((a, b) => b[1] - a[1])[0];
      return best ? best[0] : null;
    }

    function subtotal() {
      return Object.entries(qtys).reduce((s, [id, q]) => {
        if (!q) return s;
        const v = allById[id];
        return v ? s + (v.price || 0) * q : s;
      }, 0);
    }

    function cellHtml(v) {
      return `
        <div class="m-qty-wrap">
          <input class="m-qty" type="number" min="0" step="1" data-id="${v.id}" value="${qtys[v.id] || ""}" placeholder="0" inputmode="numeric">
          <div class="m-price">${UI.fmtMoney(v.price)}</div>
        </div>`;
    }

    function matrizHtml(m) {
      if (!m.rowAttr) return `<p class="erp-empty">Sem variações para esta marca.</p>`;
      const corner = m.rowAttr.label || "Característica";
      const cornerTip = tipValor(m.rowAttr.label || "", "");
      const rowTd = (row) => `
        <td class="m-row">
          <span class="m-row-val">${UI.escapeHtml(row.value)}</span>
          ${row.tip ? `<span class="tip" data-tip="${UI.escapeHtml(row.tip)}">?</span>` : ""}
        </td>`;
      if (!m.colAttr) {
        return `
          <table class="m-grid m-grid--1col">
            <thead><tr>
              <th class="m-corner">${UI.escapeHtml(corner)} <span class="tip" data-tip="${UI.escapeHtml(cornerTip)}">?</span></th>
              <th class="m-col">Quantidade</th>
            </tr></thead>
            <tbody>
              ${m.rows.map((row) => {
                const v = row.cells[0].variant;
                return `<tr>${rowTd(row)}<td class="m-cell">${v ? cellHtml(v) : `<span class="m-na">—</span>`}</td></tr>`;
              }).join("")}
            </tbody>
          </table>`;
      }
      return `
        <table class="m-grid">
          <thead>
            <tr>
              <th class="m-corner">${UI.escapeHtml(corner)} <span class="tip" data-tip="${UI.escapeHtml(cornerTip)}">?</span></th>
              <th class="m-colspan" colspan="${m.rows.length ? m.rows[0].cells.length : 1}">${UI.escapeHtml(m.colAttr.label)} <span class="tip" data-tip="${UI.escapeHtml(tipValor(m.colAttr.label, ""))}">?</span></th>
            </tr>
            <tr>
              <th class="m-corner"></th>
              ${m.rows.length ? m.rows[0].cells.map((c) => `<th class="m-col">${UI.escapeHtml(c.colValue)}</th>`).join("") : ""}
            </tr>
          </thead>
          <tbody>
            ${m.rows.map((row) => `<tr>${rowTd(row)}${row.cells.map((c) => c.variant ? `<td class="m-cell">${cellHtml(c.variant)}</td>` : `<td class="m-cell is-empty"></td>`).join("")}</tr>`).join("")}
          </tbody>
        </table>`;
    }

    function renderMatriz($wrap) {
      const $mtx = $wrap.querySelector("#mmMatriz");
      const m = buildVariationMatrix(filtered(), { attrs: p.attrs || [] });
      $mtx.innerHTML = matrizHtml(m);
      $mtx.querySelectorAll(".m-qty").forEach((i) => {
        i.oninput = () => {
          qtys[Number(i.dataset.id)] = parseInt(i.value, 10) || 0;
          atualizarResumo($wrap);
        };
      });
      atualizarResumo($wrap);
    }

    function atualizarResumo($wrap) {
      const $sub = $wrap.querySelector("#mmSubtotal");
      const $melhor = $wrap.querySelector("#mmMelhor");
      const $forn = $wrap.querySelector("#mmFornecedor");
      if ($sub) $sub.textContent = UI.fmtMoney(subtotal());
      if ($melhor) {
        const mp = melhorPrecoUn(filtered());
        $melhor.textContent = mp != null ? `${UI.fmtMoney(mp)} / un` : "—";
      }
      if ($forn) {
        const f = fornecedorSugerido();
        $forn.textContent = f || "— (definir na cotação)";
      }
    }

    function adicionar($wrap) {
      const selecionadas = Object.entries(qtys).filter(([, q]) => q > 0);
      if (!selecionadas.length) {
        UI.toast("Digite ao menos uma quantidade na matriz", "error");
        return;
      }
      let totalAdd = 0;
      selecionadas.forEach(([id, q]) => {
        const v = allById[id];
        if (!v) return;
        const specs = [];
        (p.attrs || []).forEach((a) => {
          const val = v.attrs ? v.attrs[String(a.id)] : undefined;
          if (val != null && String(val) !== "") specs.push(String(val));
        });
        Cart.addItem(v.id, q, {
          name: p.name || "",
          spec: specs.join(" · "),
          brand: v.brand || "",
          price: v.price || 0,
          imagem_url: v.imagem_url || p.imagem_url || "",
        });
        totalAdd += q;
      });
      UI.closeModal();
      UI.toast(`${totalAdd} item(ns) adicionado(s) à sua cotação`, "success");
    }

    const corpo = () => `
      <div class="modal-head">
        <div class="mm-head">
          <div class="mm-img">${p.imagem_url ? `<img src="${UI.escapeHtml(p.imagem_url)}" alt="">` : `<span class="mm-img-ph">sem imagem</span>`}</div>
          <div class="mm-title">
            <h3>${UI.escapeHtml(p.name)}</h3>
            ${pkgLabel ? `<span class="p-badge">${UI.escapeHtml(pkgLabel)}</span>` : ""}
            <p class="mm-sub">Preencha a quantidade desejada em cada célula. Vazio ou 0 = não selecionado.</p>
          </div>
        </div>
        <button class="icon-btn" data-close>×</button>
      </div>
      ${brands.length ? `
        <div class="m-brands" role="tablist">
          ${brands.map((b) => `<button type="button" class="m-brand-tab ${b === selBrand ? "is-active" : ""}" data-brand="${UI.escapeHtml(b)}">${UI.escapeHtml(b)}</button>`).join("")}
        </div>` : ""}
      <div class="mm-body">
        <div class="mm-scroll" id="mmMatriz"></div>
      </div>
      <div class="mm-foot">
        <div class="mm-resumo">
          <div class="mm-resumo-linha"><span>Subtotal estimado</span><strong id="mmSubtotal">R$ 0,00</strong></div>
          <div class="mm-resumo-linha"><span>Melhor preço / un</span><span id="mmMelhor">—</span></div>
          <div class="mm-resumo-linha"><span>Fornecedor sugerido</span><span id="mmFornecedor">—</span></div>
        </div>
        <button class="btn btn--accent" id="mmAdd">Adicionar à cotação</button>
      </div>`;

    UI.openModal(corpo(), {
      modalClass: "modal--wide",
      onMount(modal) {
        const $wrap = modal;
        modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
        modal.querySelectorAll(".m-brand-tab").forEach((b) => {
          b.onclick = () => {
            selBrand = b.dataset.brand;
            modal.querySelectorAll(".m-brand-tab").forEach((x) => x.classList.toggle("is-active", x === b));
            renderMatriz($wrap);
          };
        });
        modal.querySelector("#mmAdd").onclick = () => adicionar($wrap);
        renderMatriz($wrap);
      },
    });
  }

  function refreshGridSelection($app) {
    $app.querySelectorAll(".p-card").forEach((card) => {
      if (card.dataset.group) {
        const p = items.find((x) => x.group && x.id === Number(card.dataset.group));
        const n = p ? p.variants.reduce((s, v) => s + (draft.itens[v.id] || 0), 0) : 0;
        card.classList.toggle("is-selected", n > 0);
        const $btn = card.querySelector(".p-pick");
        if ($btn) $btn.innerHTML = `${n > 0 ? `${n} no carrinho · ` : ""}Escolher variação`;
      } else {
        const id = Number(card.dataset.id);
        const q = draft.itens[id] || 0;
        card.classList.toggle("is-selected", q > 0);
        const $q = card.querySelector(".p-qty");
        if ($q) $q.value = q;
        let $tag = card.querySelector(".p-in-cart");
        if (q > 0) {
          if (!$tag) {
            $tag = document.createElement("p");
            $tag.className = "p-in-cart";
            card.querySelector(".p-body").appendChild($tag);
          }
          $tag.textContent = `${q} no carrinho`;
        } else if ($tag) {
          $tag.remove();
        }
      }
    });
  }

  document.addEventListener("cart:updated", () => {
    draft = Cart.load();
    if (currentApp) {
      renderDraftBar(currentApp);
      refreshGridSelection(currentApp);
    }
  });

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  return { render };
})();
