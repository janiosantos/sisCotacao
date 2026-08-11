// pages/categorias.ts — Árvore de categorias/subcategorias com listagem
// paginada de produtos por subcategoria e reclassificação.
import { api, type CategoriaTree, type ProdutoSubcategoria } from "../api/client";
import { escapeHtml } from "../ui/format";
import { toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;
let dadosCache: CategoriaTree[] = [];
let selectedSubId: number | null = null;
let expandedCatIds = new Set<number>();
let prodPagina = 0;
const PROD_LIMITE = 60;
let prodCache: ProdutoSubcategoria[] = [];
let prodTotal = 0;
let prodCarregando = false;
const selecionados = new Set<number>();

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  $app.innerHTML = `<div class="loading">Carregando...</div>`;
  await recarregarDados();
  await renderTela();
}

async function recarregarDados(): Promise<void> {
  try {
    dadosCache = (await api.listarCategoriasTree()) || [];
  } catch {
    toast("Erro ao carregar categorias", "error");
    dadosCache = [];
  }
}

function subSelecionada(): { cat: CategoriaTree; sub: CategoriaTree["subcategorias"][number] } | null {
  if (selectedSubId === null) return null;
  for (const cat of dadosCache) {
    const sub = cat.subcategorias.find((s) => s.id === selectedSubId);
    if (sub) return { cat, sub };
  }
  return null;
}

function renderArvore(): string {
  return dadosCache
    .map((cat) => {
      const contemAtiva = cat.subcategorias.some((s) => s.id === selectedSubId);
      const aberta = expandedCatIds.has(cat.id) || contemAtiva;
      const chevron = cat.subcategorias.length ? (aberta ? "▼" : "▶") : "";
      const total = cat.subcategorias.reduce((a, s) => a + s.product_count, 0);
      const subsHtml = aberta
        ? cat.subcategorias
            .map(
              (sub) => `
        <div class="cat-tree-sub ${sub.id === selectedSubId ? "is-active" : ""}" data-sub-id="${sub.id}">
          <span class="cts-nome">${escapeHtml(sub.nome)}</span>
          <span class="cts-count">${sub.product_count}</span>
        </div>`
            )
            .join("")
        : "";
      return `
      <div class="cat-tree-cat">
        <div class="ctc-head" data-cat-id="${cat.id}">
          <span class="ctc-chevron">${chevron}</span>
          <span class="ctc-nome">${escapeHtml(cat.nome)}</span>
          <span class="ctc-count">${total}</span>
        </div>
        <div class="ctc-subs">${subsHtml}</div>
      </div>`;
    })
    .join("");
}

function renderDetalheCat(cat: CategoriaTree): string {
  const subsHtml = cat.subcategorias
    .map(
      (sub) => `
    <div class="cat-sub-row" data-id="${sub.id}">
      <input class="cat-sub-input" type="text" value="${escapeHtml(sub.nome)}" data-sub-id="${sub.id}">
      <span class="cat-sub-count">${sub.product_count} prods</span>
      <button class="btn btn--sm btn--ghost cat-sub-save" data-id="${sub.id}" title="Salvar">💾</button>
      <button class="btn btn--sm btn--ghost btn--danger cat-sub-del" data-id="${sub.id}" title="Excluir">✕</button>
    </div>`
    )
    .join("");
  return `
    <div class="cat-detail">
      <div class="cat-detail-head">
        <h2>${escapeHtml(cat.nome)}</h2>
        <span class="cat-detail-count">${cat.subcategorias.length} subcategorias · ${cat.subcategorias.reduce((a, s) => a + s.product_count, 0)} produtos</span>
      </div>
      <div class="cat-detail-field">
        <label>Nome da categoria</label>
        <div class="cat-detail-rename">
          <input type="text" id="catRenameInput" value="${escapeHtml(cat.nome)}">
          <button class="btn btn--sm" id="catRenameBtn">Renomear</button>
          <button class="btn btn--sm btn--ghost btn--danger" id="catDeleteBtn">Excluir categoria</button>
        </div>
      </div>
      <div class="cat-detail-subsection">
        <h3>Subcategorias</h3>
        <div class="cat-sub-add">
          <input type="text" id="catNewSubInput" placeholder="Nova subcategoria...">
          <button class="btn btn--sm btn--accent" id="catNewSubBtn">Adicionar</button>
        </div>
        <div class="cat-sub-list">${subsHtml}</div>
      </div>
      <p class="cat-detail-hint">Clique na categoria na árvore para gerenciar subcategorias. Clique numa <strong>subcategoria</strong> para ver os produtos.</p>
    </div>`;
}

async function renderProdutos(
  cat: CategoriaTree,
  sub: CategoriaTree["subcategorias"][number]
): Promise<string> {
  if (!prodCache.length && !prodCarregando) {
    await carregarProdutos(sub.id, 0);
  }

  const totalPaginas = Math.max(1, Math.ceil(prodTotal / PROD_LIMITE));
  const inicio = prodCache.length ? prodPagina * PROD_LIMITE + 1 : 0;
  const fim = prodCache.length ? prodPagina * PROD_LIMITE + prodCache.length : 0;

  const linhasHtml = prodCache
    .map(
      (p) => `
      <tr class="${selecionados.has(p.id) ? "is-selected" : ""}">
        <td class="cprod-check"><input type="checkbox" class="cprod-cb" data-id="${p.id}" ${selecionados.has(p.id) ? "checked" : ""}></td>
        <td class="cprod-nome">${escapeHtml(p.nome)}</td>
        <td class="cprod-marca">${escapeHtml(p.marca || "")}</td>
        <td class="cprod-external">${escapeHtml(p.external_id || "")}</td>
        <td class="cprod-preco">${p.price_min != null ? "R$ " + p.price_min.toFixed(2) : "—"}</td>
      </tr>`
    )
    .join("");

  const paginacaoHtml =
    prodTotal > PROD_LIMITE
      ? `
      <div class="cprod-pag">
        <button class="btn btn--sm ${prodPagina === 0 ? "is-disabled" : ""}" id="pgAnt">← Anterior</button>
        <span>Página ${prodPagina + 1} de ${totalPaginas} · ${inicio}–${fim} de ${prodTotal}</span>
        <button class="btn btn--sm ${prodPagina >= totalPaginas - 1 ? "is-disabled" : ""}" id="pgProx">Próxima →</button>
      </div>`
      : `<div class="cprod-total muted">${prodTotal} produto(s)</div>`;

  return `
    <div class="cat-detail">
      <div class="cat-detail-head">
        <h2>${escapeHtml(sub.nome)}</h2>
        <span class="cat-detail-count">${escapeHtml(cat.nome)} · ${prodTotal} produtos</span>
      </div>
      <div class="cprod-bar">
        <label class="cprod-selectall">
          <input type="checkbox" id="cprodSelectAll"> Selecionar tudo
        </label>
        <select id="cprodDestCat"><option value="">Mover para categoria…</option>
          ${dadosCache.map((c) => `<option value="${escapeHtml(c.nome)}">${escapeHtml(c.nome)}</option>`).join("")}
        </select>
        <select id="cprodDestSub"><option value="">…subcategoria</option></select>
        <button class="btn btn--sm btn--accent" id="cprodMover">Mover selecionados</button>
        <span id="cprodSelCount" class="cprod-selcount muted"></span>
      </div>
      <div class="cprod-table-wrap">
        <table class="cprod-table">
          <thead>
            <tr><th></th><th>Produto</th><th>Marca</th><th>External ID</th><th>Menor preço</th></tr>
          </thead>
          <tbody>${linhasHtml}</tbody>
        </table>
        ${prodCarregando && !prodCache.length ? `<div class="loading">Carregando produtos…</div>` : ""}
        ${!prodCache.length && !prodCarregando ? `<p class="muted cprod-vazio">Nenhum produto nesta subcategoria.</p>` : ""}
      </div>
      ${paginacaoHtml}
    </div>
  `;
}

async function renderTela(): Promise<void> {
  if (!currentApp) return;
  const carregar = subSelecionada();

  let mainHtml: string;
  if (carregar) {
    mainHtml = await renderProdutos(carregar.cat, carregar.sub);
  } else {
    const catAtiva = dadosCache.find((c) => c.id === firstExpandedOrActive());
    mainHtml = catAtiva ? renderDetalheCat(catAtiva) : `
      <div class="cat-detail cat-detail--empty">
        <p>Clique numa <strong>categoria</strong> para gerenciar, ou numa <strong>subcategoria</strong> para ver os produtos.</p>
      </div>`;
  }

  currentApp.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Categorias</h1>
      <p class="page-sub">Navegue pela árvore e clique numa subcategoria para ver produtos.</p>
    </div>
    <div class="cat-layout">
      <div class="cat-sidebar">
        <div class="cat-sidebar-head">
          <strong>${dadosCache.length} categorias</strong>
          <button class="btn btn--sm btn--accent" id="btnNovaCat">+ Nova</button>
        </div>
        <div class="cat-list-scroll cat-tree">${renderArvore()}</div>
      </div>
      <div class="cat-main">${mainHtml}</div>
    </div>
  `;

  bindEvents();
}

let expandedTargetId: number | null = null;
function firstExpandedOrActive(): number | null {
  if (expandedTargetId !== null) return expandedTargetId;
  return expandedCatIds.values().next().value ?? null;
}

function bindEvents(): void {
  const $app = currentApp;
  if (!$app) return;

  // Expande/colapsa categoria + abre detalhe da categoria
  $app.querySelectorAll<HTMLElement>(".ctc-head").forEach((el) => {
    el.onclick = () => {
      const catId = Number(el.dataset.catId);
      expandedTargetId = catId;
      if (expandedCatIds.has(catId)) expandedCatIds.delete(catId);
      else expandedCatIds.add(catId);
      selectedSubId = null;
      prodCache = [];
      prodTotal = 0;
      prodPagina = 0;
      selecionados.clear();
      void renderTela();
    };
  });

  // Seleciona subcategoria
  $app.querySelectorAll<HTMLElement>(".cat-tree-sub").forEach((el) => {
    el.onclick = () => {
      selectedSubId = Number(el.dataset.subId);
      expandedTargetId = null;
      prodCache = [];
      prodTotal = 0;
      prodPagina = 0;
      selecionados.clear();
      void renderTela();
    };
  });

  // Nova categoria
  $app.querySelector<HTMLElement>("#btnNovaCat")!.onclick = () => {
    const nome = prompt("Nome da nova categoria:");
    if (nome && nome.trim()) {
      void criarCategoria(nome.trim());
    }
  };

  // Renomear categoria
  $app.querySelector<HTMLElement>("#catRenameBtn")?.addEventListener("click", () => {
    const cat = catDetalheAtual();
    const input = $app.querySelector<HTMLInputElement>("#catRenameInput");
    if (!cat || !input) return;
    const val = input.value.trim();
    if (val && val !== cat.nome) void editarCategoria(cat.id, val);
  });

  // Excluir categoria
  $app.querySelector<HTMLElement>("#catDeleteBtn")?.addEventListener("click", async () => {
    const cat = catDetalheAtual();
    if (!cat) return;
    if (!confirm(`Excluir "${cat.nome}" e todas as subcategorias?`)) return;
    await excluirCategoria(cat.id);
    expandedTargetId = null;
  });

  // Nova subcategoria
  $app.querySelector<HTMLElement>("#catNewSubBtn")?.addEventListener("click", () => {
    const cat = catDetalheAtual();
    const input = $app.querySelector<HTMLInputElement>("#catNewSubInput");
    if (!cat || !input) return;
    const val = input.value.trim();
    if (val) {
      input.value = "";
      void criarSubcategoria(cat.id, val);
    }
  });

  $app.querySelector<HTMLInputElement>("#catNewSubInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      ($app.querySelector<HTMLElement>("#catNewSubBtn") as HTMLButtonElement)?.click();
    }
  });

  // Salvar subcategoria
  $app.querySelectorAll<HTMLElement>(".cat-sub-save").forEach((btn) => {
    btn.onclick = () => {
      const subId = Number(btn.dataset.id);
      const input = $app.querySelector<HTMLInputElement>(`.cat-sub-input[data-sub-id="${subId}"]`);
      if (!input) return;
      const val = input.value.trim();
      if (val) void editarSubcategoria(subId, val);
    };
  });

  $app.querySelectorAll<HTMLInputElement>(".cat-sub-input").forEach((input) => {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const subId = input.dataset.subId;
        if (subId) {
          const btn = $app.querySelector<HTMLElement>(`.cat-sub-save[data-id="${subId}"]`);
          btn?.click();
        }
      }
    });
  });

  // Excluir subcategoria
  $app.querySelectorAll<HTMLElement>(".cat-sub-del").forEach((btn) => {
    btn.onclick = async () => {
      const subId = Number(btn.dataset.id);
      if (!confirm("Excluir esta subcategoria?")) return;
      await excluirSubcategoria(subId);
    };
  });

  // ---- Painel de produtos ----
  $app.querySelectorAll<HTMLInputElement>(".cprod-cb").forEach((cb) => {
    cb.onchange = () => {
      const pid = Number(cb.dataset.id);
      if (cb.checked) selecionados.add(pid);
      else selecionados.delete(pid);
      atualizarSelecao($app);
    };
  });

  const selAll = $app.querySelector<HTMLInputElement>("#cprodSelectAll");
  if (selAll) {
    selAll.onchange = () => {
      for (const cb of $app.querySelectorAll<HTMLInputElement>(".cprod-cb")) {
        cb.checked = selAll.checked;
        const pid = Number(cb.dataset.id);
        if (selAll.checked) selecionados.add(pid);
        else selecionados.delete(pid);
      }
      atualizarSelecao($app);
    };
  }

  $app.querySelector<HTMLSelectElement>("#cprodDestCat")?.addEventListener("change", () => {
    const catSel = $app.querySelector<HTMLSelectElement>("#cprodDestCat");
    const subSel = $app.querySelector<HTMLSelectElement>("#cprodDestSub");
    if (!catSel || !subSel) return;
    const catNome = catSel.value;
    const cat = dadosCache.find((c) => c.nome === catNome);
    subSel.innerHTML = cat
      ? `<option value="">…subcategoria</option>` +
        cat.subcategorias.map((s) => `<option value="${escapeHtml(s.nome)}">${escapeHtml(s.nome)}</option>`).join("")
      : `<option value="">…subcategoria</option>`;
  });

  $app.querySelector<HTMLElement>("#cprodMover")?.addEventListener("click", async () => {
    const catSel = $app.querySelector<HTMLSelectElement>("#cprodDestCat");
    const subSel = $app.querySelector<HTMLSelectElement>("#cprodDestSub");
    if (!catSel || !subSel) return;
    const catNome = catSel.value;
    const subNome = subSel.value;
    if (!catNome && !subNome) {
      toast("Escolha a categoria de destino", "error");
      return;
    }
    if (!selecionados.size) {
      toast("Nenhum produto selecionado", "error");
      return;
    }
    const ids = [...selecionados];
    try {
      const r = await api.reclassificarProdutos(ids, catNome, subNome);
      toast(`${r.count} produto(s) movido(s)`, "success");
      selecionados.clear();
      await recarregarDados();
      const ativa = subSelecionada();
      if (ativa) await carregarProdutos(ativa.sub.id, 0);
      await renderTela();
    } catch (e) {
      toast("Erro ao mover: " + (e as Error).message, "error");
    }
  });

  // Paginação
  $app.querySelector<HTMLElement>("#pgAnt")?.addEventListener("click", () => {
    const ativa = subSelecionada();
    if (!ativa || prodPagina === 0) return;
    void carregarProdutos(ativa.sub.id, prodPagina - 1);
  });
  $app.querySelector<HTMLElement>("#pgProx")?.addEventListener("click", () => {
    const ativa = subSelecionada();
    if (!ativa) return;
    const totalPaginas = Math.max(1, Math.ceil(prodTotal / PROD_LIMITE));
    if (prodPagina >= totalPaginas - 1) return;
    void carregarProdutos(ativa.sub.id, prodPagina + 1);
  });
}

function atualizarSelecao($app: HTMLElement): void {
  const cont = $app.querySelector<HTMLElement>("#cprodSelCount");
  if (cont) cont.textContent = selecionados.size ? `${selecionados.size} selecionado(s)` : "";
}

function catDetalheAtual(): CategoriaTree | undefined {
  return dadosCache.find((c) => c.id === firstExpandedOrActive());
}

async function carregarProdutos(subId: number, pagina: number): Promise<void> {
  if (prodCarregando) return;
  prodCarregando = true;
  try {
    const r = await api.listarProdutosSubcategoria(subId, pagina * PROD_LIMITE, PROD_LIMITE);
    if (selectedSubId !== subId) return;
    prodCache = r.items;
    prodTotal = r.total;
    prodPagina = pagina;
    selecionados.clear();
  } catch (e) {
    toast("Erro ao carregar produtos: " + (e as Error).message, "error");
  } finally {
    prodCarregando = false;
  }
}

async function criarCategoria(nome: string): Promise<void> {
  try {
    await api.criarCategoria(nome);
    toast("Categoria criada", "success");
    await recarregarDados();
    await renderTela();
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
  }
}

async function editarCategoria(id: number, nome: string): Promise<void> {
  try {
    await api.atualizarCategoria(id, nome);
    toast("Categoria renomeada", "success");
    await recarregarDados();
    await renderTela();
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
  }
}

async function excluirCategoria(id: number): Promise<void> {
  try {
    await api.excluirCategoria(id);
    selectedSubId = null;
    expandedTargetId = null;
    toast("Categoria excluida", "success");
    await recarregarDados();
    await renderTela();
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
  }
}

async function criarSubcategoria(catId: number, nome: string): Promise<void> {
  try {
    await api.criarSubcategoria(catId, nome);
    toast("Subcategoria adicionada", "success");
    await recarregarDados();
    await renderTela();
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
  }
}

async function editarSubcategoria(id: number, nome: string): Promise<void> {
  try {
    await api.atualizarSubcategoria(id, nome);
    toast("Subcategoria renomeada", "success");
    await recarregarDados();
    await renderTela();
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
  }
}

async function excluirSubcategoria(id: number): Promise<void> {
  try {
    await api.excluirSubcategoria(id);
    toast("Subcategoria excluida", "success");
    await recarregarDados();
    await renderTela();
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
  }
}
