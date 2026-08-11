// pages/catalogo.ts — catálogo (filtros + grid) e seleção de variações por matriz.

import { api, type Atributo, type CatalogoItem, type CategoriaMap, type ListCatalogo, type ProdutoGrupo, type ProdutoResumo, type Variante } from "../api/client";
import * as Cart from "../cart";
import { escapeHtml, fmtMoney } from "../ui/format";
import { closeModal, confirmDialog, openModal, toast } from "../ui/dom";

let categorias: CategoriaMap = {};
let filters: { categoria: string; subcategoria: string; q: string; classe: string; ordenar: string } = { categoria: "", subcategoria: "", q: "", classe: "", ordenar: "" };
let items: CatalogoItem[] = [];
let total = 0;
let page = 1;
let loading = false;
let draft = Cart.load();
let currentApp: HTMLElement | null = null;
let agrupado = true;

const PAGE = 60;

// ---------------- matriz 2D de variações (utilidade) ----------------

function naturalCompare(a: string | number, b: string | number): number {
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

function orderedOptions(attr: Atributo, vset: Variante[]): (string | number)[] {
  const seen = new Set<string>();
  const vals: (string | number)[] = [];
  (attr.options || []).forEach((o) => {
    const key = String(o);
    if (!seen.has(key)) {
      seen.add(key);
      vals.push(o);
    }
  });
  vset.forEach((v) => {
    const val = v.attrs ? v.attrs[String(attr.id)] : undefined;
    if (val == null) return;
    const key = String(val);
    if (!seen.has(key)) {
      seen.add(key);
      vals.push(val as string | number);
    }
  });
  return vals.sort(naturalCompare);
}

interface MatrixCell {
  colValue: string | null;
  variant: Variante | null;
}

interface MatrixRow {
  value: string | number;
  tip: string;
  cells: MatrixCell[];
}

interface MatrixResult {
  rowAttr: Atributo | null;
  colAttr: Atributo | null;
  rows: MatrixRow[];
}

function buildVariationMatrix(variations: Variante[], meta: { attrs?: Atributo[] }): MatrixResult {
  let attrs = (meta && meta.attrs) || [];
  let vset = variations || [];
  const usable = attrs.filter((a) => vset.some((v) => v.attrs && v.attrs[String(a.id)] != null));
  const DIM = /bitola|di[âa]metro|tamanho|medida|capacidade|pot[eê]ncia|tens[aã]o|voltagem|corrente|amperagem|comprimento|volume|peso|quantidade|rolo|embalagem|mm|w\b|litros|kg|metro|pol/i;

  let row: Atributo | null = null;
  let col: Atributo | null = null;
  if (usable.length === 1) {
    row = usable[0];
  } else if (usable.length >= 2) {
    const dims = usable.filter((a) => DIM.test(a.label || ""));
    row = dims[0] || usable[0];
    col = usable.find((a) => a.id !== row!.id) || null;
  }

  // Some legacy products have multiple variants but no family/attribute rows.
  // Keep them selectable instead of hiding the variants from the matrix.
  if (!row && vset.length > 1) {
    const fallback: Atributo = {
      id: -1,
      label: "Variação / SKU",
      options: vset.map((v) => v.sku || `#${v.id}`),
    };
    attrs = [fallback];
    vset = vset.map((v) => ({
      ...v,
      attrs: { ...(v.attrs || {}), "-1": v.sku || `#${v.id}` },
    }));
    row = fallback;
  }

  if (!row) {
    return { rowAttr: null, colAttr: null, rows: [] };
  }

  const rowValues = orderedOptions(row, vset);
  const colValues = col ? orderedOptions(col, vset) : ["_"];

  const cellMap: Record<string, Record<string, Variante>> = {};
  vset.forEach((v) => {
    const rv = v.attrs ? v.attrs[String(row.id)] : undefined;
    if (rv == null) return;
    const cv = col ? String(v.attrs?.[String(col.id)] ?? "_") : "_";
    const keyR = String(rv);
    cellMap[keyR] = cellMap[keyR] || {};
    const prev = cellMap[keyR][cv];
    if (!prev || (v.price != null && (prev.price == null || v.price < prev.price))) {
      cellMap[keyR][cv] = v;
    }
  });

  const rows: MatrixRow[] = rowValues.map((value) => ({
    value,
    tip: tipValor(row!.label || "", value),
    cells: colValues.map((cv) => ({
      colValue: cv === "_" ? null : String(cv),
      variant: cellMap[String(value)] && cellMap[String(value)][cv] ? cellMap[String(value)][cv] : null,
    })),
  }));

  return { rowAttr: row, colAttr: col, rows };
}

function freeCellKey(parts: Array<[number, string]>): string {
  return parts.map(([id, v]) => `${id}=${encodeURIComponent(v)}`).join("&");
}

function freeCellAttrs(key: string): Record<number, string> {
  const out: Record<number, string> = {};
  String(key)
    .split("&")
    .forEach((part) => {
      const eq = part.indexOf("=");
      if (eq <= 0) return;
      out[Number(part.slice(0, eq))] = decodeURIComponent(part.slice(eq + 1));
    });
  return out;
}

function cartItemKey(descricao: string): number {
  let h = 2166136261;
  for (let i = 0; i < descricao.length; i++) {
    h = Math.imul(h ^ descricao.charCodeAt(i), 16777619);
  }
  if (!h) h = 1;
  return -(Math.abs(h >>> 0) || 1);
}

// ---------------- tooltips educativos ----------------

const ATTR_TIPS: Record<string, string> = {
  bitola: "Bitola = seção do condutor. Quanto maior, maior a corrente que o cabo suporta.",
  diametro: "Diâmetro da peça (mm ou polegadas).",
  tamanho: "Tamanho / medida da peça.",
  medida: "Medida do produto.",
  tensao: "Tensão de operação. Confira a instalação: 127V ou 220V.",
  voltagem: "Tensão de operação (127V ou 220V).",
  potencia: "Consumo elétrico em watts. Mais watts = mais potência/brilho.",
  "temperatura de cor": "Tom da luz: fria (trabalho), neutra (áreas gerais), quente (conforto).",
  cor: "Cor da peça. Escolha a desejada.",
  capacidade: "Capacidade que o produto comporta (volume/massa).",
  embalagem: "Forma de venda (rolo inteiro ou avulso, por exemplo).",
};
const TIPS_VALORES: Record<string, Record<string, string>> = {
  bitola: {
    "1,5": "Ideal para iluminação",
    "2,5": "Tomadas de uso geral",
    "4": "Chuveiros até 5.500W",
    "6": "Chuveiros elétricos potentes",
    "10": "Torneiras elétricas / centrais",
  },
  tensao: {
    "127v": "Padrão residencial (110–127V)",
    "110v": "Padrão residencial (110–127V)",
    "220v": "Comum no interior do país (200–240V)",
    "220": "Comum no interior (200–240V)",
  },
  potencia: {
    "9w": "Menor consumo — áreas de convivência",
    "12w": "Mais brilho — áreas de trabalho",
  },
};

function normTip(s: unknown): string {
  return String(s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function tipValor(attrLabel: string, valor: unknown): string {
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

function detFromItem(p: ProdutoResumo): Partial<import("../api/client").DetalheCartItem> {
  return {
    name: p.name || "",
    spec: p.spec || "",
    brand: p.brand || "",
    price: p.price || 0,
    imagem_url: p.imagem_url || "",
  };
}

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  $app.innerHTML = `<div class="loading">Carregando catálogo…</div>`;
  try {
    categorias = await api.listarCategorias();
  } catch {
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
          <div class="field">
            <label>Curva ABC</label>
            <select id="fClasse">
              <option value="">Todas as classes</option>
              <option value="A">Classe A</option>
              <option value="B">Classe B</option>
              <option value="C">Classe C</option>
            </select>
          </div>
          <div class="field">
            <label>Ordenar por</label>
            <select id="fOrdenar">
              <option value="">Nome</option>
              <option value="abc">Curva ABC (A → C)</option>
            </select>
          </div>
          <button class="btn btn--ghost" id="btnLimpar">Limpar filtros</button>
          <button class="btn" id="btnModo"></button>
          <span class="result-count" id="resultCount"></span>
        </div>

        <div class="abc-chips" id="abcResumo"></div>

        <div id="grid" class="product-grid"></div>
        <div class="load-more" id="paginacao"></div>
      </div>
      <aside id="cartSidebar" class="cart-sidebar-slot"></aside>
    </div>
  `;
  Cart.mountSidebar($app.querySelector<HTMLElement>("#cartSidebar")!);

  const $categoria = $app.querySelector<HTMLSelectElement>("#fCategoria")!;
  for (const cat of Object.keys(categorias).sort()) {
    $categoria.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(cat)}">${escapeHtml(titleCase(cat))}</option>`);
  }
  updateSubcategoryOptions($app);

  const $search = $app.querySelector<HTMLInputElement>("#fSearch")!;
  const $hint = $app.querySelector<HTMLElement>("#searchHint")!;
  $search.addEventListener(
    "input",
    debounce((e: Event) => {
      const v = (e.target as HTMLInputElement).value.trim();
      if (v.length > 0 && v.length < 3) {
        $hint.style.display = "block";
        if (filters.q !== "") {
          filters.q = "";
          void loadProducts($app, true);
        }
        return;
      }
      $hint.style.display = "none";
      filters.q = v;
      void loadProducts($app, true);
    }, 300)
  );
  $categoria.addEventListener("change", (e) => {
    filters.categoria = (e.target as HTMLSelectElement).value;
    filters.subcategoria = "";
    updateSubcategoryOptions($app);
    void loadProducts($app, true);
  });
  $app.querySelector<HTMLSelectElement>("#fSubcategoria")!.addEventListener("change", (e) => {
    filters.subcategoria = (e.target as HTMLSelectElement).value;
    void loadProducts($app, true);
  });
  const $classe = $app.querySelector<HTMLSelectElement>("#fClasse")!;
  $classe.addEventListener("change", (e) => {
    filters.classe = (e.target as HTMLSelectElement).value;
    void loadProducts($app, true);
  });
  $app.querySelector<HTMLSelectElement>("#fOrdenar")!.addEventListener("change", (e) => {
    filters.ordenar = (e.target as HTMLSelectElement).value;
    void loadProducts($app, true);
  });
  $app.querySelector<HTMLButtonElement>("#btnLimpar")!.addEventListener("click", () => {
    filters = { categoria: "", subcategoria: "", q: "", classe: "", ordenar: "" };
    ($app.querySelector<HTMLInputElement>("#fSearch")!).value = "";
    $categoria.value = "";
    $classe.value = "";
    updateSubcategoryOptions($app);
    void loadProducts($app, true);
  });
  const $modo = $app.querySelector<HTMLButtonElement>("#btnModo")!;
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
    void loadProducts($app, true);
  });

  renderDraftBar($app);
  await loadProducts($app, true);
}

function updateSubcategoryOptions($app: HTMLElement): void {
  const $sub = $app.querySelector<HTMLSelectElement>("#fSubcategoria")!;
  $sub.innerHTML = '<option value="">Todas</option>';
  const subs = filters.categoria
    ? categorias[filters.categoria] || []
    : [...new Set(Object.values(categorias).flat())];
  for (const s of subs.slice().sort()) {
    $sub.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(s)}">${escapeHtml(titleCase(s))}</option>`);
  }
}

async function loadProducts($app: HTMLElement, reset: boolean): Promise<void> {
  if (loading) return;
  if (reset) page = 1;
  loading = true;
  try {
    const res: ListCatalogo = await api.listarProdutos({
      categoria: filters.categoria,
      subcategoria: filters.subcategoria,
      q: filters.q,
      classe: filters.classe,
      ordenar: filters.ordenar,
      offset: (page - 1) * PAGE,
      limit: PAGE,
      agrupado: agrupado ? 1 : 0,
    });
    items = res.items;
    total = res.total;
    renderGrid($app);
    renderPaginacao($app);
  } catch (e) {
    toast("Erro ao carregar catálogo: " + (e as Error).message, "error");
  } finally {
    loading = false;
    void renderAbcResumo($app);
  }
}

async function renderAbcResumo($app: HTMLElement): Promise<void> {
  const $chips = $app.querySelector<HTMLElement>("#abcResumo");
  if (!$chips) return;
  try {
    const r = await api.resumoAbc({
      categoria: filters.categoria,
      subcategoria: filters.subcategoria,
      q: filters.q,
    });
    const total = r.A + r.B + r.C + r.sem;
    const pct = (n: number) => (total ? Math.round((n / total) * 100) : 0);
    const chip = (classe: "A" | "B" | "C" | "sem", n: number, ativo: boolean) => `
      <button type="button" class="abc-chip abc-chip--${classe === "A" ? "a" : classe === "B" ? "b" : "c"}${ativo ? " is-active" : ""}"
        data-classe="${classe}" title="${classe === "sem" ? "Sem classe ABC calculada" : `Filtrar curva ${classe}`}">
        ${classe === "sem" ? "sem classe" : `Classe ${classe}`}: <strong>${n}</strong> (${pct(n)}%)</button>`;
    $chips.innerHTML = [
      chip("A", r.A, filters.classe === "A"),
      chip("B", r.B, filters.classe === "B"),
      chip("C", r.C, filters.classe === "C"),
      r.sem > 0 ? chip("sem", r.sem, filters.classe === "") : "",
    ].join("");
    $chips.querySelectorAll<HTMLButtonElement>("[data-classe]").forEach((b) => {
      b.onclick = () => {
        const c = b.dataset.classe || "";
        const $classe = $app.querySelector<HTMLSelectElement>("#fClasse");
        if ($classe) $classe.value = c === "sem" ? "" : c;
        filters.classe = c === "sem" ? "" : c;
        void loadProducts($app, true);
      };
    });
  } catch {
    $chips.innerHTML = "";
  }
}

function renderPaginacao($app: HTMLElement): void {
  const $wrap = $app.querySelector<HTMLElement>("#paginacao")!;
  const paginas = Math.max(1, Math.ceil(total / PAGE));
  if (paginas <= 1) {
    $wrap.innerHTML = "";
    return;
  }
  const atual = Math.min(Math.max(1, page), paginas);
  const botoes: string[] = [];
  const addBtn = (label: string, p: number, opts: { active?: boolean; disabled?: boolean } = {}) => {
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
  $wrap.querySelectorAll<HTMLButtonElement>("[data-page]").forEach((b) => {
    if (b.disabled) return;
    b.onclick = () => {
      page = Number(b.dataset.page);
      void loadProducts($app, false);
    };
  });
}

function renderGrid($app: HTMLElement): void {
  $app.querySelector<HTMLElement>("#resultCount")!.textContent = `${total} produto(s)`;
  const $grid = $app.querySelector<HTMLElement>("#grid")!;
  if (items.length === 0) {
    $grid.innerHTML = `<div class="empty-box" style="grid-column:1/-1;"><p>Nada encontrado</p><p>Tente outro termo de busca ou categoria.</p></div>`;
    return;
  }
  $grid.innerHTML = items.map(cardHtml).join("");
  $grid.querySelectorAll<HTMLElement>(".p-card").forEach((card) => {
    if (card.dataset.group) {
      const p = items.find((x) => "group" in x && x.group === true && x.id === Number(card.dataset.group)) as ProdutoGrupo | undefined;
      if (!p) return;
      const abrir = () => void abrirModalVariante(p);
      card.querySelector<HTMLElement>(".p-photo")!.addEventListener("click", abrir);
      card.querySelector<HTMLElement>(".p-pick")!.addEventListener("click", abrir);
      return;
    }
    const produtoId = Number(card.dataset.id);
    const item = items.find((x) => x.id === produtoId && !("group" in x && x.group)) as ProdutoResumo | undefined;
    const det = item ? detFromItem(item) : undefined;
    card.querySelector<HTMLElement>(".p-minus")!.addEventListener("click", () =>
      setQty(produtoId, Math.max(0, (draft.itens[produtoId] || 0) - 1), $app, det)
    );
    card.querySelector<HTMLElement>(".p-plus")!.addEventListener("click", () =>
      setQty(produtoId, (draft.itens[produtoId] || 0) + 1, $app, det)
    );
    card.querySelector<HTMLInputElement>(".p-qty")!.addEventListener("change", (e) =>
      setQty(produtoId, Math.max(0, parseInt((e.target as HTMLInputElement).value, 10) || 0), $app, det)
    );
    card.querySelector<HTMLElement>(".p-photo")!.addEventListener("click", () => void abrirModalProduto(produtoId));
  });
}

function cardHtml(p: CatalogoItem): string {
  if ("group" in p && p.group) return groupCardHtml(p as ProdutoGrupo);
  const prod = p as ProdutoResumo;
  const qty = draft.itens[prod.id] || 0;
  const price = fmtMoney(prod.price);
  return `
    <article class="p-card ${qty > 0 ? "is-selected" : ""}" data-id="${prod.id}">
      <div class="p-photo">${prod.imagem_url ? `<img src="${escapeHtml(prod.imagem_url)}" loading="lazy" alt="">` : `<span style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">sem imagem</span>`}</div>
      <div class="p-body">
        <p class="p-code">${prod.classe_abc ? `<span class="abc-chip abc-chip--${prod.classe_abc.toLowerCase()}" title="Curva ABC">${prod.classe_abc}</span> ` : ""}${escapeHtml(prod.sku || "#" + prod.id)}</p>
        <p class="p-desc">${escapeHtml(prod.name)}</p>
        ${prod.spec ? `<p class="p-spec">${escapeHtml(prod.spec)}</p>` : ""}
        ${prod.brand ? `<p class="p-brand">${escapeHtml(prod.brand)}</p>` : ""}
        <div class="p-price-row">
          <p class="p-price">${price}</p>
          ${prod.package_label ? `<span class="p-unit-badge">${escapeHtml(prod.package_label)}</span>` : ""}
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

function groupCardHtml(p: ProdutoGrupo): string {
  const naDraft = p.variants.reduce((s, v) => s + (draft.itens[v.id] || 0), 0);
  const pkgLabel = p.package_label || "";
  const priceLabel = p.price_min !== p.price_max ? `a partir de ${fmtMoney(p.price_min)}` : fmtMoney(p.price_min);
  return `
    <article class="p-card ${naDraft > 0 ? "is-selected" : ""}" data-group="${p.id}">
      <div class="p-photo">${p.imagem_url ? `<img src="${escapeHtml(p.imagem_url)}" loading="lazy" alt="">` : `<span style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">sem imagem</span>`}</div>
      <div class="p-body">
        <p class="p-code">${p.classe_abc ? `<span class="abc-chip abc-chip--${p.classe_abc.toLowerCase()}" title="Curva ABC">${p.classe_abc}</span> ` : ""}${pkgLabel ? `<span class="p-badge">${escapeHtml(pkgLabel)}</span>` : ""}${p.variant_count} variações</p>
        <p class="p-desc">${escapeHtml(p.name)}</p>
        <p class="p-price">${priceLabel}</p>
      </div>
      <div class="p-actions">
        <button class="btn btn--accent btn--sm p-pick">${naDraft > 0 ? `${naDraft} no carrinho · ` : ""}Escolher variação</button>
      </div>
    </article>`;
}

function setQty(produtoId: number, qty: number, $app: HTMLElement, det?: Partial<import("../api/client").DetalheCartItem>): void {
  Cart.setQty(produtoId, qty, det || {});
  draft = Cart.load();
  if (currentApp) refreshGridSelection(currentApp);
  renderDraftBar($app);
}

function renderDraftBar($app: HTMLElement): void {
  const $bar = $app ? $app.querySelector<HTMLElement>("#draftBar") : null;
  if (!$bar) return;
  const ids = Object.keys(draft.itens).filter((id) => Number(draft.itens[Number(id)]) > 0);
  if (ids.length === 0) {
    $bar.innerHTML = `<span style="color:#B9BDB2;font-size:13px;">Nenhum produto selecionado ainda. Use os controles “+” nos produtos acima.</span>`;
    return;
  }
  const totalQtd = ids.reduce((s, id) => s + draft.itens[Number(id)], 0);
  $bar.innerHTML = `
    <span><strong>${ids.length}</strong> itens · <strong>${totalQtd}</strong> unidades no carrinho</span>
    <span class="spacer"></span>
    <button class="btn btn--ghost" id="btnLimparDraft">Limpar carrinho</button>
    <button class="btn btn--accent" id="btnCriarCotacao">Criar cotação →</button>
  `;
  $bar.querySelector<HTMLElement>("#btnLimparDraft")!.addEventListener("click", async () => {
    if (!(await confirmDialog("Limpar todos os itens do carrinho atual?"))) return;
    Cart.clear();
    draft = Cart.load();
    renderGrid($app);
    renderDraftBar($app);
  });
  $bar.querySelector<HTMLElement>("#btnCriarCotacao")!.addEventListener("click", (e) => {
    void Cart.criarCotacao(e.currentTarget as HTMLElement);
  });
}

async function abrirModalProduto(produtoId: number): Promise<void> {
  let p: ProdutoResumo;
  try {
    p = await api.detalharProduto(produtoId);
  } catch {
    toast("Erro ao carregar produto", "error");
    return;
  }
  const imgs = (p as ProdutoResumo & { image_urls?: string[] }).image_urls && (p as ProdutoResumo & { image_urls?: string[] }).image_urls!.length
    ? (p as ProdutoResumo & { image_urls?: string[] }).image_urls!
    : [];
  const mainImg = imgs.length ? imgs[0] : "";
  openModal(
    `<div class="modal-head"><h3>Produto</h3><button class="icon-btn" data-close>×</button></div>
     <div class="prod-gallery">
       <img class="prod-main" id="pMain" src="${escapeHtml(mainImg)}" alt="">
       ${imgs.length > 1 ? `<div class="prod-thumbs">${imgs.map((u, i) => `<img data-src="${escapeHtml(u)}" src="${escapeHtml(u)}" class="${i === 0 ? "is-active" : ""}">`).join("")}</div>` : ""}
     </div>
     <p class="p-code" style="margin:0;">${escapeHtml(p.sku || "#" + p.id)}</p>
     <h3 style="font-family:var(--font-body);text-transform:none;font-size:16px;letter-spacing:0;margin:6px 0 0;">${escapeHtml(p.name)}</h3>
     ${p.brand ? `<div class="prod-meta">Marca: ${escapeHtml(p.brand)}</div>` : ""}
     ${(p as ProdutoResumo & { color?: string }).color ? `<div class="prod-meta">Cor: ${escapeHtml((p as ProdutoResumo & { color?: string }).color)}</div>` : ""}
     <div class="prod-price">${fmtMoney(p.price)}</div>
     ${p.pix_price ? `<div class="prod-meta" style="color:var(--green);font-weight:600;">PIX: ${fmtMoney(p.pix_price)}</div>` : ""}
     ${p.installment ? `<div class="prod-meta">${escapeHtml(p.installment)}</div>` : ""}
     <div class="prod-add">
       <input type="number" id="pQty" value="1" min="1" step="1">
       <button class="btn btn--accent" id="pAdd">Adicionar à cotação</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll<HTMLElement>("[data-close]").forEach((b) => (b.onclick = closeModal));
        const $main = modal.querySelector<HTMLImageElement>("#pMain")!;
        modal.querySelectorAll<HTMLElement>(".prod-thumbs img").forEach((t) => {
          t.addEventListener("click", () => {
            $main.src = (t as HTMLImageElement).dataset.src || "";
            modal.querySelectorAll<HTMLElement>(".prod-thumbs img").forEach((x) => x.classList.remove("is-active"));
            t.classList.add("is-active");
          });
        });
        modal.querySelector<HTMLElement>("#pAdd")!.onclick = () => {
          const qty = Math.max(1, parseInt((modal.querySelector<HTMLInputElement>("#pQty")!).value, 10) || 1);
          Cart.addItem(p.id, qty, {
            name: p.name || "",
            spec: [(p as ProdutoResumo & { color?: string }).color].filter(Boolean).join(", "),
            brand: p.brand || "",
            price: p.price || 0,
            imagem_url: mainImg || "",
          });
          closeModal();
          toast(`${qty} item(ns) adicionado(s) à sua cotação`, "success");
        };
      },
    }
  );
}

async function abrirModalVariante(p: ProdutoGrupo): Promise<void> {
  const variants = p.variants || [];
  const brands = p.brands && p.brands.length ? p.brands.slice() : [];
  let selBrand: string | null = brands.length ? brands[0] : null;
  const qtys: Record<number, number> = {};
  const allById: Record<number, Variante> = {};
  const freeQtys: Record<string, number> = {};
  const addedRows: string[] = []; // valores de bitola adicionados pelo usuário
  const addedCols: string[] = []; // valores de cor adicionados pelo usuário
  const addedQtys: Record<string, number> = {}; // key: "row|<rowVal>|col|<colVal>" -> qty
  variants.forEach((v) => {
    allById[v.id] = v;
  });
  const pkgLabel = p.package_label || "";

  const filtered = () => (selBrand ? variants.filter((v) => (v.brand || "") === selBrand) : variants);

  function melhorPrecoUn(lista: Variante[]): number | null {
    const prices = lista.map((v) => v.price).filter((x) => x != null && x > 0);
    return prices.length ? Math.min(...prices) : null;
  }

  function fornecedorSugerido(): string | null {
    const pesos: Record<string, number> = {};
    Object.entries(qtys).forEach(([id, q]) => {
      if (!q) return;
      const v = allById[Number(id)];
      if (!v) return;
      (v.fornecedores || []).forEach((n) => {
        pesos[n] = (pesos[n] || 0) + q;
      });
    });
    const best = Object.entries(pesos).sort((a, b) => b[1] - a[1])[0];
    return best ? best[0] : null;
  }

  function subtotal(): number {
    return Object.entries(qtys).reduce((s, [id, q]) => {
      if (!q) return s;
      const v = allById[Number(id)];
      return v ? s + (v.price || 0) * q : s;
    }, 0);
  }

  function simKey(m: MatrixResult, rowVal: string | number, colVal: string | number | null): string {
    const parts: Array<[number, string]> = [[m.rowAttr!.id, String(rowVal)]];
    if (m.colAttr && colVal != null) parts.push([m.colAttr.id, String(colVal)]);
    return freeCellKey(parts);
  }

  function allRowValues(m: MatrixResult): string[] {
    return [...m.rows.map((r) => String(r.value)), ...addedRows];
  }

  function allColValues(m: MatrixResult): string[] {
    if (!m.colAttr) return [];
    const existing = m.rows.length ? m.rows[0].cells.map((c) => c.colValue).filter((v): v is string => v != null) : [];
    return [...existing, ...addedCols];
  }

  function cellHtml(v: Variante): string {
    return `
      <div class="m-qty-wrap">
        <input class="m-qty" type="number" min="0" step="1" data-id="${v.id}" value="${qtys[v.id] || ""}" placeholder="0" inputmode="numeric">
        <div class="m-price">${fmtMoney(v.price)}</div>
      </div>`;
  }

  function freeCellHtml(key: string, labelTxt: string): string {
    return `
      <div class="m-qty-wrap m-qty-wrap--free">
        <input class="m-qty m-qty--free" type="number" min="0" step="1" data-key="${escapeHtml(key)}" value="${freeQtys[key] || ""}" placeholder="0" inputmode="numeric" title="${escapeHtml(labelTxt)}">
        <div class="m-price m-price--free">sob consulta</div>
      </div>`;
  }

  function addedCellHtml(rowVal: string, colVal: string | null, m: MatrixResult): string {
    const key = simKey(m, rowVal, colVal);
    const label = m.colAttr ? `${rowVal} · ${colVal}` : String(rowVal);
    return `
      <div class="m-qty-wrap m-qty-wrap--added">
        <input class="m-qty m-qty--added" type="number" min="0" step="1" data-added-key="${escapeHtml(key)}" value="${addedQtys[key] || ""}" placeholder="0" inputmode="numeric" title="${escapeHtml(label)}">
        <div class="m-price m-price--added">sob consulta</div>
      </div>`;
  }

  function addRowBtnHtml(m: MatrixResult): string {
    if (!m.rowAttr) return "";
    const label = escapeHtml(m.rowAttr.label);
    const colCount = m.colAttr ? allColValues(m).length : 1;
    return `
      <tr class="m-add-row">
        <td class="m-row" colspan="${colCount + 1}" style="text-align:left; padding:8px 10px;">
          <button type="button" class="btn btn--sm btn--ghost m-add-btn m-add-row-btn" style="width:auto; padding:4px 10px; font-size:12px;">
            + Adicionar nova ${label}
          </button>
        </td>
      </tr>`;
  }

  function addColBtnHtml(m: MatrixResult): string {
    if (!m.colAttr) return "";
    const label = escapeHtml(m.colAttr.label);
    return `
      <th class="m-col m-col--add" style="width:40px; vertical-align:middle; background:var(--bg-tray);">
        <button type="button" class="m-add-btn m-add-col-btn" title="Adicionar ${label}">+</button>
      </th>`;
  }

  function matrizHtml(m: MatrixResult): string {
    if (!m.rowAttr) return `<p class="erp-empty">Sem variações para esta marca.</p>`;
    const corner = m.rowAttr.label || "Característica";
    const cornerTip = tipValor(m.rowAttr.label || "", "");

    const rowTd = (rv: string) => {
      const isAdded = addedRows.includes(rv);
      return `
        <td class="m-row">
          <span class="m-row-val">${escapeHtml(rv)}</span>
          ${isAdded ? `<button type="button" class="m-rm-btn" data-rm-row="${escapeHtml(rv)}" title="Remover">×</button>` : ""}
          ${!isAdded ? (tipValor(m.rowAttr!.label || "", rv) ? `<span class="tip" data-tip="${escapeHtml(tipValor(m.rowAttr!.label || "", rv))}">?</span>` : "") : ""}
        </td>`;
    };

    if (!m.colAttr) {
      const rows = allRowValues(m).map((rv) => {
        const orig = m.rows.find((r) => String(r.value) === rv);
        const cell = orig && orig.cells[0].variant
          ? cellHtml(orig.cells[0].variant)
          : freeCellHtml(simKey(m, rv, null), `${corner}: ${rv}`);
        return `<tr>${rowTd(rv)}<td class="m-cell">${cell}</td></tr>`;
      }).join("");
      return `
        <table class="m-grid m-grid--1col">
          <thead><tr>
            <th class="m-corner">${escapeHtml(corner)} <span class="tip" data-tip="${escapeHtml(cornerTip)}">?</span></th>
            <th class="m-col">Quantidade</th>
          </tr></thead>
          <tbody>${rows}${addRowBtnHtml(m)}</tbody>
        </table>`;
    }

    const colVals = allColValues(m);
    const headCols = colVals.map((cv) => {
      const isAdded = addedCols.includes(cv);
      return `
        <th class="m-col">
          ${escapeHtml(cv)}
          ${isAdded ? `<button type="button" class="m-rm-btn" data-rm-col="${escapeHtml(cv)}" title="Remover">×</button>` : ""}
        </th>`;
    }).join("");

    const body = allRowValues(m).map((rv) => {
      const orig = m.rows.find((r) => String(r.value) === rv);
      const cells = colVals.map((cv) => {
        const existing = orig?.cells.find((c) => c.colValue === cv);
        if (existing?.variant) return `<td class="m-cell">${cellHtml(existing.variant)}</td>`;
        if (existing) return `<td class="m-cell">${freeCellHtml(simKey(m, rv, cv), `${rv} · ${cv}`)}</td>`;
        return `<td class="m-cell">${addedCellHtml(rv, cv, m)}</td>`;
      }).join("");
      return `<tr>${rowTd(rv)}${cells}<td class="m-cell-empty" style="background:var(--bg-tray);"></td></tr>`;
    }).join("");

    return `
      <table class="m-grid">
        <thead>
          <tr>
            <th class="m-corner">${escapeHtml(corner)} <span class="tip" data-tip="${escapeHtml(cornerTip)}">?</span></th>
            <th class="m-colspan" colspan="${colVals.length}">${escapeHtml(m.colAttr.label)} <span class="tip" data-tip="${escapeHtml(tipValor(m.colAttr.label, ""))}">?</span></th>
            <th class="m-corner" style="background:var(--bg-tray);"></th>
          </tr>
          <tr>
            <th class="m-corner"></th>
            ${headCols}
            ${addColBtnHtml(m)}
          </tr>
        </thead>
        <tbody>${body}${addRowBtnHtml(m)}</tbody>
      </table>`;
  }

  function renderMatriz($wrap: HTMLElement): void {
    const $mtx = $wrap.querySelector<HTMLElement>("#mmMatriz")!;
    const m = buildVariationMatrix(filtered(), { attrs: p.attrs || [] });
    $mtx.innerHTML = matrizHtml(m);
    $mtx.querySelectorAll<HTMLInputElement>(".m-qty[data-id]").forEach((i) => {
      i.oninput = () => {
        qtys[Number(i.dataset.id)] = parseInt(i.value, 10) || 0;
        atualizarResumo($wrap);
      };
    });
    $mtx.querySelectorAll<HTMLInputElement>(".m-qty--free").forEach((i) => {
      i.oninput = () => {
        freeQtys[i.dataset.key || ""] = parseInt(i.value, 10) || 0;
        atualizarResumo($wrap);
      };
    });
    $mtx.querySelectorAll<HTMLInputElement>(".m-qty--added").forEach((i) => {
      i.oninput = () => {
        addedQtys[i.dataset.addedKey || ""] = parseInt(i.value, 10) || 0;
        atualizarResumo($wrap);
      };
    });
    $mtx.querySelectorAll<HTMLButtonElement>(".m-add-row-btn").forEach((b) => {
      b.onclick = () => {
        const val = prompt(`Nova ${m.rowAttr?.label || "linha"}:`);
        if (val && val.trim()) {
          addedRows.push(val.trim());
          renderMatriz($wrap);
        }
      };
    });
    $mtx.querySelectorAll<HTMLButtonElement>(".m-add-col-btn").forEach((b) => {
      b.onclick = () => {
        const val = prompt(`Nova ${m.colAttr?.label || "coluna"}:`);
        if (val && val.trim()) {
          addedCols.push(val.trim());
          renderMatriz($wrap);
        }
      };
    });
    $mtx.querySelectorAll<HTMLButtonElement>(".m-rm-btn").forEach((b) => {
      b.onclick = () => {
        const r = b.dataset.rmRow;
        const c = b.dataset.rmCol;
        if (r) {
          const idx = addedRows.indexOf(r);
          if (idx !== -1) addedRows.splice(idx, 1);
        }
        if (c) {
          const idx = addedCols.indexOf(c);
          if (idx !== -1) addedCols.splice(idx, 1);
        }
        // Limpa qtys associadas a esse row/col
        Object.keys(addedQtys).forEach((key) => {
          if (r && key.includes(`=${encodeURIComponent(r)}`)) delete addedQtys[key];
          if (c && key.includes(`=${encodeURIComponent(c)}`)) delete addedQtys[key];
        });
        renderMatriz($wrap);
      };
    });
    atualizarResumo($wrap);
  }

  function atualizarResumo($wrap: HTMLElement): void {
    const $sub = $wrap.querySelector<HTMLElement>("#mmSubtotal");
    const $melhor = $wrap.querySelector<HTMLElement>("#mmMelhor");
    const $forn = $wrap.querySelector<HTMLElement>("#mmFornecedor");
    if ($sub) $sub.textContent = fmtMoney(subtotal());
    if ($melhor) {
      const mp = melhorPrecoUn(filtered());
      $melhor.textContent = mp != null ? `${fmtMoney(mp)} / un` : "—";
    }
    if ($forn) {
      const f = fornecedorSugerido();
      $forn.textContent = f || "— (definir na cotação)";
    }
  }

  function adicionar(): void {
    const selecionadas = Object.entries(qtys).filter(([, q]) => q > 0);
    const livreSel = Object.entries(freeQtys).filter(([, q]) => q > 0);
    const addedSel = Object.entries(addedQtys).filter(([, q]) => q > 0);
    if (!selecionadas.length && !livreSel.length && !addedSel.length) {
      toast("Digite ao menos uma quantidade na matriz", "error");
      return;
    }
    let totalAdd = 0;
    selecionadas.forEach(([id, q]) => {
      const v = allById[Number(id)];
      if (!v) return;
      const specs: string[] = [];
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
    livreSel.forEach(([key, q]) => {
      const attrs = freeCellAttrs(key);
      const specs: string[] = [];
      (p.attrs || []).forEach((a) => {
        const val = attrs[a.id];
        if (val != null && val !== "") specs.push(`${a.label}: ${val}`);
      });
      const descricao = specs.join(" · ") || p.name || "";
      Cart.addCustomItem(cartItemKey(key), q, {
        name: p.name || "",
        spec: specs.join(" · "),
        brand: selBrand || "",
        price: 0,
        imagem_url: p.imagem_url || "",
        custom: true,
        descricao,
        produto_pai: p.id,
        marca: selBrand || "",
        atributos: { ...attrs },
      });
      totalAdd += q;
    });
    addedSel.forEach(([key, q]) => {
      const attrs = freeCellAttrs(key);
      const specs: string[] = [];
      (p.attrs || []).forEach((a) => {
        const val = attrs[a.id];
        if (val != null && val !== "") specs.push(`${a.label}: ${val}`);
      });
      const descricao = specs.join(" · ") || p.name || "";
      Cart.addCustomItem(cartItemKey(key), q, {
        name: p.name || "",
        spec: specs.join(" · "),
        brand: selBrand || "",
        price: 0,
        imagem_url: p.imagem_url || "",
        custom: true,
        descricao,
        produto_pai: p.id,
        marca: selBrand || "",
        atributos: { ...attrs },
      });
      totalAdd += q;
    });
    closeModal();
    toast(`${totalAdd} item(ns) adicionado(s) à sua cotação`, "success");
  }

  const corpo = () => `
    <div class="modal-head">
      <div class="mm-head">
        <div class="mm-img">${p.imagem_url ? `<img src="${escapeHtml(p.imagem_url)}" alt="">` : `<span class="mm-img-ph">sem imagem</span>`}</div>
        <div class="mm-title">
          <h3>${escapeHtml(p.name)}</h3>
          ${pkgLabel ? `<span class="p-badge">${escapeHtml(pkgLabel)}</span>` : ""}
          <p class="mm-sub">Preencha a quantidade desejada em cada célula. Vazio ou 0 = não selecionado.</p>
        </div>
      </div>
      <button class="icon-btn" data-close>×</button>
    </div>
    ${brands.length ? `
      <div class="m-brands" role="tablist">
        ${brands.map((b) => `<button type="button" class="m-brand-tab ${b === selBrand ? "is-active" : ""}" data-brand="${escapeHtml(b)}">${escapeHtml(b)}</button>`).join("")}
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

  openModal(corpo(), {
    modalClass: "modal--wide",
    onMount(modal) {
      const $wrap = modal;
      modal.querySelectorAll<HTMLElement>("[data-close]").forEach((b) => (b.onclick = closeModal));
      modal.querySelectorAll<HTMLElement>(".m-brand-tab").forEach((b) => {
        b.onclick = () => {
          selBrand = b.dataset.brand || null;
          modal.querySelectorAll<HTMLElement>(".m-brand-tab").forEach((x) => x.classList.toggle("is-active", x === b));
          renderMatriz($wrap);
        };
      });
      modal.querySelector<HTMLElement>("#mmAdd")!.onclick = () => adicionar();
      renderMatriz($wrap);
    },
  });
}

function refreshGridSelection($app: HTMLElement): void {
  $app.querySelectorAll<HTMLElement>(".p-card").forEach((card) => {
    if (card.dataset.group) {
      const p = items.find((x) => "group" in x && x.group === true && x.id === Number(card.dataset.group)) as ProdutoGrupo | undefined;
      const n = p ? p.variants.reduce((s, v) => s + (draft.itens[v.id] || 0), 0) : 0;
      card.classList.toggle("is-selected", n > 0);
      const $btn = card.querySelector<HTMLElement>(".p-pick");
      if ($btn) $btn.innerHTML = `${n > 0 ? `${n} no carrinho · ` : ""}Escolher variação`;
    } else {
      const id = Number(card.dataset.id);
      const q = draft.itens[id] || 0;
      card.classList.toggle("is-selected", q > 0);
      const $q = card.querySelector<HTMLInputElement>(".p-qty");
      if ($q) $q.value = String(q);
      let $tag = card.querySelector<HTMLElement>(".p-in-cart");
      if (q > 0) {
        if (!$tag) {
          $tag = document.createElement("p");
          $tag.className = "p-in-cart";
          card.querySelector<HTMLElement>(".p-body")!.appendChild($tag);
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

function debounce(fn: (e: Event) => void, ms: number): (e: Event) => void {
  let t: ReturnType<typeof setTimeout> | undefined;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function titleCase(s: string): string {
  if (!s) return s;
  return s.toLowerCase().replace(/(^|\s|\/|\()([a-zà-ÿ])/g, (_m, sep: string, c: string) => sep + c.toUpperCase());
}
