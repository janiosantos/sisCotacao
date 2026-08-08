// pages/produtos.ts — cadastro de produtos (famílias + produto pai + variações + imagens).
// Port de catalog_server/static/page_produtos.js.

import {
  api,
  type Familia,
  type FamiliaAtributo,
  type FamiliaPayload,
  type Fornecedor,
  type FornecedorVariante,
  type FornecedorVariantePayload,
  type ItemListaCadastro,
  type ProdutoCadastro,
  type ProdutoCadastroPayload,
  type ProdutoPreview,
} from "../api/client";
import { escapeHtml, fmtMoney } from "../ui/format";
import { closeModal, confirmDialog, openModal, toast } from "../ui/dom";

let familias: Familia[] = [];
let categoriasSugestoes: string[] = [];
let categoriasTree: Record<string, string[]> = {};
let fornecedores: Fornecedor[] = []; // lista p/ códigos por fornecedor

// ---------------- estado da lista ----------------
let filters = { q: "", familia_id: "" } as { q: string; familia_id: string };
let items: ItemListaCadastro[] = [];
let total = 0;
let page = 1;
let loading = false;
const PAGE = 60;

// ---------------- estado do editor ----------------
type Atributo = Omit<FamiliaAtributo, "obrigatorio"> & {
  obrigatorio: number | boolean;
};

let atributos: Atributo[] = []; // defs da família selecionada
let valores: Record<number, Set<string>> = {}; // attrId -> Set(valores)
let variantes: VarianteLocal[] = []; // {id?, sku, ean, preco, prom, valores:{attrId:value}}
let fornecedorEdits: Record<string, FornecedorEdit> = {}; // "fornecedorId:idx" -> {codigo, unidade, fator, descricao}

interface VarianteLocal {
  id?: number;
  sku: string;
  ean: string;
  preco: string | number;
  prom: string | number;
  valores: Record<string, string>;
}

interface FornecedorEdit {
  codigo: string;
  unidade: string;
  fator: string | number;
  descricao: string;
}

const FORN_EDIT_VAZIO: FornecedorEdit = { codigo: "", unidade: "", fator: "", descricao: "" };

function debounce<T extends (...args: never[]) => void>(fn: T, ms: number): (...args: Parameters<T>) => void {
  let t: ReturnType<typeof setTimeout> | undefined;
  return (...args: Parameters<T>) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function carregarCategorias(): Promise<void> {
  try {
    const tree = await api.listarCategorias();
    categoriasTree = tree;
    const list: string[] = [];
    for (const [cat, subs] of Object.entries(tree)) {
      list.push(cat);
      (subs || []).forEach((s) => list.push(`${cat} > ${s}`));
    }
    categoriasSugestoes = [...new Set(list)].sort((a, b) => a.localeCompare(b, "pt"));
  } catch {
    categoriasSugestoes = [];
    categoriasTree = {};
  }
}

function atualizarSubsugestoes(categoria: string): void {
  const subs = (categoriasTree[categoria] || [])
    .slice()
    .sort((a, b) => a.localeCompare(b, "pt"));
  const dl = document.getElementById("dlSubcategorias") as HTMLDataListElement | null;
  if (dl) dl.innerHTML = subs.map((s) => `<option value="${escapeHtml(s)}">`).join("");
}

// ===================================================================
// LISTA
// ===================================================================

export async function renderLista($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando produtos…</div>`;
  try {
    familias = await api.listarFamilias();
  } catch {
    familias = [];
  }
  await carregarCategorias();

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Produtos</h1>
        <p class="page-sub">Cadastre produtos por família e geração de variações (modelo TOTVS).</p>
      </div>
    </div>

    <div class="toolbar">
      <div class="field" style="min-width:240px;flex:1;">
        <label>Buscar</label>
        <input id="fSearch" type="text" placeholder="Nome, marca, código…" autocomplete="off">
        <p class="search-hint" id="searchHint">Digite ao menos 3 caracteres para buscar.</p>
      </div>
      <div class="field">
        <label>Família</label>
        <select id="fFamilia"><option value="">Todas</option></select>
      </div>
      <button class="btn btn--outline" id="btnFamilias">Famílias</button>
      <button class="btn btn--outline" id="btnNovoUrl">Novo via URL</button>
      <button class="btn btn--accent" id="btnNovo">Novo produto</button>
      <span class="result-count" id="resultCount"></span>
    </div>

    <div id="grid" class="product-grid"></div>
    <div class="load-more" id="paginacao"></div>
  `;

  const $familia = $app.querySelector<HTMLSelectElement>("#fFamilia");
  if ($familia) {
    for (const f of familias) {
      $familia.insertAdjacentHTML("beforeend", `<option value="${f.id}">${escapeHtml(f.nome)}</option>`);
    }
  }

  const $search = $app.querySelector<HTMLInputElement>("#fSearch");
  const $hint = $app.querySelector<HTMLElement>("#searchHint");
  if ($search && $hint) {
    $search.addEventListener("input", debounce((e: Event) => {
      const v = (e.target as HTMLInputElement).value.trim();
      if (v.length > 0 && v.length < 3) {
        $hint.style.display = "block";
        if (filters.q !== "") {
          filters.q = "";
          void carregar($app, true);
        }
        return;
      }
      $hint.style.display = "none";
      filters.q = v;
      void carregar($app, true);
    }, 300));
  }
  if ($familia) {
    $familia.addEventListener("change", (e) => {
      filters.familia_id = (e.target as HTMLSelectElement).value;
      void carregar($app, true);
    });
  }
  $app.querySelector("#btnFamilias")?.addEventListener("click", () => void abrirModalFamilias($app));
  $app.querySelector("#btnNovoUrl")?.addEventListener("click", () => void abrirModalImportarUrl());
  $app.querySelector("#btnNovo")?.addEventListener("click", () => { location.hash = "#/produtos/novo"; });

  void carregar($app, true);
}

async function carregar($app: HTMLElement, reset: boolean): Promise<void> {
  if (loading) return;
  if (reset) page = 1;
  loading = true;
  try {
    const res = await api.listarProdutosCadastro({
      q: filters.q,
      familia_id: filters.familia_id || undefined,
      offset: (page - 1) * PAGE,
      limit: PAGE,
    });
    items = res.items;
    total = res.total;
    renderGrid($app);
    renderPaginacao($app);
  } catch (e) {
    toast("Erro ao carregar produtos: " + (e as Error).message, "error");
  } finally {
    loading = false;
  }
}

function renderPaginacao($app: HTMLElement): void {
  const $wrap = $app.querySelector("#paginacao");
  if (!($wrap instanceof HTMLElement)) return;
  const paginas = Math.max(1, Math.ceil(total / PAGE));
  if (paginas <= 1) { $wrap.innerHTML = ""; return; }
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
  $wrap.querySelectorAll<HTMLElement>("[data-page]").forEach((b) => {
    if ((b as HTMLButtonElement).disabled) return;
    b.onclick = () => {
      page = Number(b.dataset.page);
      void carregar($app, false);
    };
  });
}

function renderGrid($app: HTMLElement): void {
  const $count = $app.querySelector("#resultCount");
  if ($count) $count.textContent = `${total} produto(s)`;
  const $grid = $app.querySelector("#grid");
  if (!($grid instanceof HTMLElement)) return;
  if (!items.length) {
    $grid.innerHTML = filters.q
      ? `<div class="empty-box" style="grid-column:1/-1;"><p>Nenhum produto encontrado para a busca.</p><p>Confira os termos digitados ou busque por SKU/EAN.</p></div>`
      : `<div class="empty-box" style="grid-column:1/-1;"><p>Nenhum produto cadastrado</p><p>Clique em "Novo produto" para começar.</p></div>`;
    return;
  }
  $grid.innerHTML = items.map(cardHtml).join("");
  $grid.querySelectorAll<HTMLElement>(".p-card").forEach((card) => {
    const id = Number(card.dataset.id);
    card.querySelector<HTMLElement>(".p-pick")?.addEventListener("click", () => { location.hash = `#/produtos/${id}`; });
    card.querySelector<HTMLElement>(".p-del")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      const ok = await confirmDialog("Excluir este produto e todas as suas variações e imagens?");
      if (!ok) return;
      try {
        await api.excluirProdutoCadastro(id);
        toast("Produto excluído", "success");
        void carregar($app, true);
      } catch (err) {
        toast("Erro ao excluir: " + (err as Error).message, "error");
      }
    });
  });
}

function cardHtml(p: ItemListaCadastro): string {
  const price = p.price_min ? `a partir de ${fmtMoney(p.price_min)}` : "sem preço";
  const badgeClasse = p.classe_abc
    ? `<span class="abc-chip abc-chip--${p.classe_abc.toLowerCase()}">${p.classe_abc}</span>`
    : "";
  const badgeLinha = p.em_linha === 0
    ? `<span class="abc-chip abc-chip--fora" title="Fora do rolar (equipamento de alto valor)">fora</span>`
    : "";
  return `
    <article class="p-card" data-id="${p.id}">
      <div class="p-photo">${p.imagem_url ? `<img src="${escapeHtml(p.imagem_url)}" loading="lazy" alt="">` : `<span style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">sem imagem</span>`}</div>
      <div class="p-body">
        <p class="p-code"><span class="p-badge">${escapeHtml(p.familia_nome || "Sem família")}</span> ${p.variant_count} variações ${badgeClasse} ${badgeLinha}</p>
        <p class="p-desc">${escapeHtml(p.nome)}</p>
        ${p.marca ? `<p class="p-brand">${escapeHtml(p.marca)}</p>` : ""}
        <p class="p-price">${price}</p>
      </div>
      <div class="p-actions" style="display:flex;gap:6px;align-items:center;">
        <button class="btn btn--accent btn--sm p-pick">Editar</button>
        <button class="btn btn--danger btn--sm p-del">Excluir</button>
      </div>
    </article>`;
}

// ===================================================================
// FAMÍLIAS (gestão)
// ===================================================================

async function abrirModalFamilias($app: HTMLElement): Promise<void> {
  const refresh = async () => {
    familias = await api.listarFamilias();
    await renderLista($app);
  };
  const corpo = () => {
    if (!familias.length) return `<p style="font-size:13px;color:var(--ink-soft);">Nenhuma família cadastrada ainda.</p>`;
    return familias.map((f) => `
      <div class="fam-row">
        <div style="flex:1;">
          <strong>${escapeHtml(f.nome)}</strong>
          <div style="font-size:12px;color:var(--ink-soft);">${f.atributos.length} atributo(s): ${escapeHtml(f.atributos.map((a) => a.nome).join(", "))}</div>
        </div>
        <button class="btn btn--sm" data-edit="${f.id}">Editar</button>
        <button class="btn btn--danger btn--sm" data-del="${f.id}">Excluir</button>
      </div>`).join("");
  };
  openModal(`
    <div class="modal-head"><h3>Famílias</h3><button class="icon-btn" data-close>×</button></div>
    <div id="famLista" style="display:flex;flex-direction:column;gap:8px;max-height:60vh;overflow-y:auto;">${corpo()}</div>
    <div class="modal-actions">
      <button class="btn" data-close>Fechar</button>
      <button class="btn btn--accent" id="btnNovaFamilia">Nova família</button>
    </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelectorAll<HTMLElement>("[data-edit]").forEach((b) => {
          b.onclick = async () => {
            const f = familias.find((x) => x.id === Number(b.dataset.edit));
            if (!f) return;
            const saved = await abrirModalFamiliaForm(f);
            if (saved) { closeModal(); void refresh(); }
          };
        });
        modal.querySelectorAll<HTMLElement>("[data-del]").forEach((b) => {
          b.onclick = async () => {
            const f = familias.find((x) => x.id === Number(b.dataset.del));
            if (!f) return;
            if (!(await confirmDialog(`Excluir a família "${f.nome}"?`))) return;
            try {
              await api.excluirFamilia(f.id);
              toast("Família excluída", "success");
              void refresh();
            } catch (e) {
              toast("Erro: " + (e as Error).message, "error");
            }
          };
        });
        modal.querySelector<HTMLElement>("#btnNovaFamilia")!.onclick = async () => {
          const saved = await abrirModalFamiliaForm(null);
          if (saved) { closeModal(); void refresh(); }
        };
      },
    }
  );
}

function abrirModalFamiliaForm(familia: Familia | null): Promise<boolean | { id: number; nome: string }> {
  return new Promise((resolve) => {
    let atributosForm: {
      id: number | null;
      nome: string;
      tipo: "lista" | "livre";
      opcoes: string[];
      obrigatorio: boolean;
    }[] = (familia ? familia.atributos : []).map((a) => ({
      id: a.id,
      nome: a.nome,
      tipo: a.tipo,
      opcoes: a.opcoes || [],
      obrigatorio: !!a.obrigatorio,
    }));
    if (!atributosForm.length) atributosForm = [{ id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false }];

    const rowHtml = (a: typeof atributosForm[number], i: number) => `
      <div class="fa-row" data-i="${i}">
        <input class="fa-nome" data-i="${i}" type="text" placeholder="Nome do atributo (ex.: Cor)" value="${escapeHtml(a.nome)}">
        <select class="fa-tipo" data-i="${i}">
          <option value="lista" ${a.tipo === "lista" ? "selected" : ""}>Lista de opções</option>
          <option value="livre" ${a.tipo === "livre" ? "selected" : ""}>Valor livre</option>
        </select>
        <input class="fa-opcoes" data-i="${i}" type="text" placeholder="azul, vermelho, preto (separado por vírgula)" value="${escapeHtml(a.opcoes.join(", "))}">
        <label class="fa-obrig" title="Obriga a informar ao menos um valor deste atributo ao cadastrar o produto">
          <input type="checkbox" class="fa-obrig-check" data-i="${i}" ${a.obrigatorio ? "checked" : ""}> Obrig.
        </label>
        <button class="icon-btn" data-rm="${i}">×</button>
      </div>`;

    const corpo = () => `
      <div class="modal-head"><h3>${familia ? "Editar família" : "Nova família"}</h3><button class="icon-btn" data-close>×</button></div>
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div class="field"><label>Nome da família *</label><input id="faNome" type="text" value="${escapeHtml(familia ? familia.nome : "")}" placeholder="Ex.: Cabo Flexível, Parafuso, Cola"></div>
        <div class="field"><label>Descrição (opcional)</label><input id="faDesc" type="text" value="${escapeHtml(familia ? familia.descricao : "")}"></div>
        <div class="field">
          <label>Atributos (características das variações)</label>
          <div id="faLista" style="display:flex;flex-direction:column;gap:6px;">${atributosForm.map(rowHtml).join("")}</div>
          <button class="btn btn--ghost btn--sm" id="faAdd" style="margin-top:8px;">+ Adicionar atributo</button>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn" data-cancel>Cancelar</button>
        <button class="btn btn--accent" id="faSalvar">Salvar</button>
      </div>`;

    openModal(corpo(), {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("[data-cancel]")!.onclick = () => { closeModal(); resolve(false); };

        function collect(): FamiliaPayload["atributos"] {
          return atributosForm.map((a, i) => ({
            id: a.id,
            nome: modal.querySelector<HTMLInputElement>(`.fa-nome[data-i="${i}"]`)!.value.trim(),
            tipo: modal.querySelector<HTMLSelectElement>(`.fa-tipo[data-i="${i}"]`)!.value,
            opcoes: modal.querySelector<HTMLInputElement>(`.fa-opcoes[data-i="${i}"]`)!.value
              .split(",").map((s) => s.trim()).filter(Boolean),
            obrigatorio: !!modal.querySelector<HTMLInputElement>(`.fa-obrig-check[data-i="${i}"]`)!.checked,
          })).filter((a) => a.nome);
        }
        function syncFromDom(): void {
          modal.querySelectorAll<HTMLElement>("#faLista .fa-row").forEach((row, i) => {
            if (!atributosForm[i]) return;
            atributosForm[i].nome = row.querySelector<HTMLInputElement>(".fa-nome")!.value;
            atributosForm[i].tipo = row.querySelector<HTMLSelectElement>(".fa-tipo")!.value as "lista" | "livre";
            atributosForm[i].opcoes = row.querySelector<HTMLInputElement>(".fa-opcoes")!.value
              .split(",").map((s) => s.trim()).filter(Boolean);
            atributosForm[i].obrigatorio = !!row.querySelector<HTMLInputElement>(".fa-obrig-check")!.checked;
          });
        }
        function rebuild(): void {
          syncFromDom();
          modal.querySelector<HTMLElement>("#faLista")!.innerHTML = atributosForm.map(rowHtml).join("");
          modal.querySelectorAll<HTMLElement>("#faLista [data-rm]").forEach((b) => {
            b.onclick = () => { atributosForm.splice(Number(b.dataset.rm), 1); rebuild(); };
          });
        }
        modal.querySelectorAll<HTMLElement>("#faLista [data-rm]").forEach((b) => {
          b.onclick = () => { atributosForm.splice(Number(b.dataset.rm), 1); rebuild(); };
        });
        modal.querySelector<HTMLElement>("#faAdd")!.onclick = () => {
          atributosForm.push({ id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false });
          rebuild();
        };
        modal.querySelector<HTMLElement>("#faSalvar")!.onclick = async () => {
          const nome = modal.querySelector<HTMLInputElement>("#faNome")!.value.trim();
          if (!nome) { toast("Informe o nome da família", "error"); return; }
          const payload: FamiliaPayload = {
            nome,
            descricao: modal.querySelector<HTMLInputElement>("#faDesc")!.value.trim(),
            atributos: collect(),
          };
          try {
            if (familia) {
              await api.atualizarFamilia(familia.id, payload);
              resolve(true);
            } else {
              const res = await api.criarFamilia(payload);
              resolve({ id: res.id, nome });
            }
            toast("Família salva", "success");
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    });
  });
}

// ===================================================================
// IMPORTAR POR URL
// ===================================================================

function previewHtml(p: ProdutoPreview): string {
  const linhas: (string | number | null | undefined)[][] = [
    ["Produto", p.nome],
    ["Marca", p.marca],
    ["SKU / EAN", [p.sku, p.ean].filter(Boolean).join(" / ")],
    ["Família", p.familia_nome],
    ["Preço", p.preco != null ? fmtMoney(p.preco) : "—"],
    ["À vista (PIX)", p.preco_pix != null ? fmtMoney(p.preco_pix) : "—"],
    ["De", p.preco_de != null ? fmtMoney(p.preco_de) : "—"],
    ["Parcelamento", p.parcelamento],
    ["Fotos", p.fotos],
  ];
  const attrs = (p.atributos || []).map((a) => `${escapeHtml(a.label)}: <strong>${escapeHtml(a.valor)}</strong>`).join(" · ");
  return `
    <div class="preview-box" style="border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:12px;">
      <table style="width:100%;font-size:13px;border-collapse:collapse;">
        ${linhas.filter(([, v]) => v).map(([k, v]) => `
          <tr style="border-bottom:1px solid var(--line);">
            <td style="padding:5px 8px;color:var(--ink-soft);width:140px;">${k}</td>
            <td style="padding:5px 8px;"><strong>${escapeHtml(String(v))}</strong></td>
          </tr>`).join("")}
        ${attrs ? `<tr><td style="padding:5px 8px;color:var(--ink-soft);vertical-align:top;">Atributos</td><td style="padding:5px 8px;">${attrs}</td></tr>` : ""}
      </table>
    </div>`;
}

function abrirModalImportarUrl(): void {
  openModal(`
    <div class="modal-head"><h3>Cadastrar a partir de URL</h3><button class="icon-btn" data-close>×</button></div>
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div class="field">
        <label>URL do produto</label>
        <input id="iuUrl" type="text" placeholder="https://www.casadoeletricistasc.com.br/...">
      </div>
      <p style="font-size:12px;color:var(--ink-soft);">O sistema lê a página e cria automaticamente a família, os atributos e baixa as fotos. Você confere o resultado antes de confirmar.</p>
      <div id="iuPreview"></div>
    </div>
    <div class="modal-actions">
      <button class="btn" data-close>Cancelar</button>
      <button class="btn btn--accent" id="iuAnalisar">Analisar URL</button>
      <button class="btn btn--accent" id="iuCadastrar" style="display:none;">Cadastrar produto</button>
    </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        const $url = modal.querySelector<HTMLInputElement>("#iuUrl")!;
        const $prev = modal.querySelector<HTMLElement>("#iuPreview")!;
        const $analisar = modal.querySelector<HTMLButtonElement>("#iuAnalisar")!;
        const $cadastrar = modal.querySelector<HTMLButtonElement>("#iuCadastrar")!;
        let parsed: ProdutoPreview | null = null;

        $analisar.onclick = async () => {
          const url = $url.value.trim();
          if (!url) { toast("Informe a URL do produto", "error"); return; }
          $analisar.disabled = true;
          $analisar.textContent = "Analisando…";
          $prev.innerHTML = `<p style="font-size:13px;color:var(--ink-soft);">Buscando informações do produto…</p>`;
          try {
            parsed = await api.parseUrlProduto(url);
            $prev.innerHTML = previewHtml(parsed);
            $cadastrar.style.display = "";
            toast("Produto identificado", "success");
          } catch (e) {
            $prev.innerHTML = `<p style="font-size:13px;color:var(--ink-faint);">Erro: ${escapeHtml((e as Error).message)}</p>`;
          } finally {
            $analisar.disabled = false;
            $analisar.textContent = "Analisar URL";
          }
        };

        $cadastrar.onclick = async () => {
          if (!parsed) return;
          $cadastrar.disabled = true;
          $cadastrar.textContent = "Cadastrando…";
          try {
            const res = await api.criarProdutoPorUrl(parsed.url);
            closeModal();
            toast(`Produto cadastrado (${res.imagens_baixadas} foto(s) baixada(s))`, "success");
            if (res.imagens_erros) toast(`${res.imagens_erros} foto(s) não puderam ser baixadas`, "error");
            location.hash = `#/produtos/${res.id}`;
          } catch (e) {
            toast("Erro ao cadastrar: " + (e as Error).message, "error");
            $cadastrar.disabled = false;
            $cadastrar.textContent = "Cadastrar produto";
          }
        };
      },
    }
  );
}

// ===================================================================
// EDITOR DE PRODUTO
// ===================================================================

export async function renderEditor($app: HTMLElement, produtoId: number | null): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando…</div>`;
  if (!familias.length) {
    try { familias = await api.listarFamilias(); } catch { familias = []; }
  }
  await carregarCategorias();

  let produto: ProdutoCadastro | null = null;
  if (produtoId) {
    try {
      produto = await api.detalharProdutoCadastro(produtoId);
    } catch {
      toast("Erro ao carregar produto", "error");
      location.hash = "#/produtos";
      return;
    }
  }

  const familiaInicial = produto ? produto.familia_id : familias[0] ? familias[0].id : null;
  carregarAtributosFamilia(familiaInicial, produto);

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">${produto ? "Editar produto" : "Novo produto"}</h1>
        <p class="page-sub">Cadastre o produto uma vez; as variações são geradas pelas combinações dos atributos.</p>
      </div>
      <button class="btn btn--ghost" id="btnVoltar">← Voltar</button>
    </div>

    <div class="erp-editor">

      <!-- Abas corporativas (Folders) -->
      <div class="erp-tabs" role="tablist">
        <button type="button" class="erp-tab is-active" data-tab="gerais">Dados Gerais</button>
        <button type="button" class="erp-tab" data-tab="atributos">Atributos da Família</button>
        <button type="button" class="erp-tab" data-tab="variacoes">Matriz de Variações</button>
        <button type="button" class="erp-tab" data-tab="imagens">Mídia e Anexos</button>
      </div>

      <!-- Aba 1: Dados Gerais (com painel de gestão / Curva ABC) -->
      <div class="erp-panel is-active" id="tab-gerais">
        <div class="ed-layout">
          <div class="ed-fields">
            <div class="field ed-span2">
              <label>Família *</label>
              <div class="ed-family-row">
                <select id="eFamilia">
                  ${familias.map((f) => `<option value="${f.id}" ${f.id === familiaInicial ? "selected" : ""}>${escapeHtml(f.nome)}</option>`).join("")}
                </select>
                <button class="btn btn--outline btn--sm" id="btnNovaFamiliaEditor" title="Criar família e seus atributos">+ Nova família</button>
              </div>
            </div>
            <div class="field">
              <label>Marca</label>
              <input id="eMarca" type="text" value="${escapeHtml(produto ? produto.marca : "")}" placeholder="Ex.: Corfio">
            </div>
            <div class="field ed-span2">
              <label>Nome base do produto *</label>
              <input id="eNome" type="text" value="${escapeHtml(produto ? produto.nome : "")}" placeholder="Ex.: Cabo Flexível 750V Antichama">
              <div class="nome-padrao">
                <div class="nome-padrao-hint">
                  <span class="info-icone" title="Padrão de nomenclatura de fábrica (guia suave): o sistema sugere a estrutura e monta o nome, mas você pode ajustar livremente depois.">?</span>
                  <span id="ePadraoText">Padrão: <em>Item</em> + <em>Características</em> (bitola, tensão, CA) + <em>Marca</em>.</span>
                </div>
                <button class="btn btn--ghost btn--sm" id="btnMontarPadrao" type="button">Montar pelo padrão</button>
              </div>
            </div>
            <div class="field">
              <label>Categoria (opcional)</label>
              <input id="eCategoria" list="dlCategorias" type="text" value="${escapeHtml(produto ? produto.categoria : "")}" placeholder="Fios e Cabos">
              <datalist id="dlCategorias">${categoriasSugestoes.map((c) => `<option value="${escapeHtml(c)}">`).join("")}</datalist>
            </div>
            <div class="field">
              <label>Subcategoria (opcional)</label>
              <input id="eSubcategoria" list="dlSubcategorias" type="text" value="${escapeHtml(produto ? produto.subcategoria : "")}" placeholder="Cabo Flexível">
              <datalist id="dlSubcategorias"></datalist>
            </div>
            <div class="field ed-span2">
              <label>Descrição (opcional)</label>
              <input id="eDesc" type="text" value="${escapeHtml(produto ? produto.descricao : "")}" title="Descrição comercial do produto">
            </div>
            <div class="field ed-span2">
              <label>Termos de busca / sinônimos</label>
              <input id="eTermosBusca" type="text" value="${escapeHtml(produto ? produto.termos_busca || "" : "")}" placeholder="Ex.: cabo, fio, 750V, antichama, barramento…">
              <p class="field-hint">Palavras-chave e variações do nome usado pelo mercado, para facilitar a busca (ex.: "fio" além de "cabo").</p>
            </div>
          </div>
          <aside class="ed-gestao">
            <div class="ed-gestao-head">Curva ABC &middot; Gestão de Linha</div>
            <div id="eAbcRecap" class="abc-recap"></div>
          </aside>
        </div>
      </div>

      <!-- Aba 2: Atributos da Família -->
      <div class="erp-panel hidden" id="tab-atributos">
        <p class="erp-panel-info">Combine os valores dos atributos da família selecionada. Os marcados ficam ativos na aba de variações.</p>
        <div id="eAtributos"></div>
      </div>

      <!-- Aba 3: Matriz de Variações (Data Grid comercial) -->
      <div class="erp-panel hidden" id="tab-variacoes">
        <div class="vt-toolbar">
          <button class="btn btn--accent btn--sm" id="btnGerar">Gerar Variações</button>
          <p id="eVariantesHint" class="vt-hint"></p>
        </div>
        <div class="vt-scroll">
          <div id="eVariantes" class="vt-grid-wrap"></div>
        </div>
        ${produto ? `
        <div class="vt-supplier">
          <div class="vt-supplier-head">
            <h4>Códigos por fornecedor</h4>
            <p style="margin:0;font-size:11px;color:var(--erp-ink-soft);">Código usado pelo fornecedor para cada variação, unidade de compra e fator de conversão (ex.: embalagem com 10 unidades &rarr; fator 10).</p>
          </div>
          <div class="vt-supplier-controls">
            <select id="fvFornecedor"><option value="">Selecione o fornecedor…</option></select>
            <button class="btn btn--accent btn--sm" id="btnSalvarFornecedor">Salvar códigos</button>
          </div>
          <div id="fvGrid" class="vt-supplier-grid"></div>
        </div>` : `
        <p class="vt-supplier-empty" style="margin-top:10px;">Salve o produto para cadastrar os códigos dos fornecedores por variação.</p>`}
      </div>

      <!-- Aba 4: Mídia e Anexos (Imagens) -->
      <div class="erp-panel hidden" id="tab-imagens">
        ${produto ? `
        <div class="img-tools">
          <label class="btn btn--ghost btn--sm">Enviar arquivos
            <input type="file" id="imgUpload" accept="image/*" multiple hidden>
          </label>
          <input id="imgUrl" type="text" placeholder="URL da página do produto ou imagem direta" style="flex:1;">
          <button class="btn btn--accent btn--sm" id="btnBaixarUrl">Baixar da internet</button>
        </div>
        <div id="imgGrid" class="img-grid"></div>` : `
        <p class="erp-empty">Salve o produto para poder adicionar imagens.</p>`}
      </div>

      <div class="form-actions">
        <button class="btn" id="btnCancelar">Cancelar</button>
        <button class="btn btn--accent" id="btnSalvar">Salvar produto</button>
      </div>
    </div>
  `;

  bindEditor($app, produto);
}

function carregarAtributosFamilia(familiaId: number | null, produto: ProdutoCadastro | null): void {
  const f = familias.find((x) => x.id === familiaId);
  atributos = f ? (f.atributos || []) : [];
  if (produto && produto.atributos && produto.familia_id === familiaId) {
    atributos = produto.atributos;
  }
  // inicializa valores e variações
  valores = {};
  atributos.forEach((a) => { valores[a.id] = new Set(); });
  variantes = [];
  if (produto && produto.familia_id === familiaId) {
    (produto.variantes || []).forEach((v) => {
      const vals: Record<string, string> = {};
      atributos.forEach((a) => {
        const val = v.atributos ? v.atributos[String(a.id)] : undefined;
        if (val) { valores[a.id].add(val); vals[String(a.id)] = val; }
      });
      variantes.push({ id: v.id, sku: v.sku || "", ean: v.ean || "", preco: v.preco || "", prom: v.preco_promocional || "", valores: vals });
    });
  }
}

function bindEditor($app: HTMLElement, produto: ProdutoCadastro | null): void {
  $app.querySelector<HTMLElement>("#btnVoltar")!.onclick = () => { location.hash = "#/produtos"; };
  $app.querySelector<HTMLElement>("#btnCancelar")!.onclick = () => { location.hash = "#/produtos"; };

  // ---- Navegação corporativa por abas (Folders) ----
  const $tabs = $app.querySelector(".erp-tabs");
  if ($tabs) {
    $tabs.addEventListener("click", (e) => {
      const tab = (e.target as HTMLElement).closest(".erp-tab");
      if (!tab) return;
      $app.querySelectorAll(".erp-tab").forEach((b) => b.classList.toggle("is-active", b === tab));
      $app.querySelectorAll(".erp-panel").forEach((p) => p.classList.add("hidden"));
      const panel = $app.querySelector<HTMLElement>("#tab-" + (tab as HTMLElement).dataset.tab);
      if (panel) panel.classList.remove("hidden");
    });
  }

  $app.querySelector<HTMLSelectElement>("#eFamilia")!.addEventListener("change", (e) => {
    carregarAtributosFamilia(Number((e.target as HTMLSelectElement).value), null);
    renderAtributos($app);
    renderVariantes($app);
  });

  const $btnNovaFamilia = $app.querySelector("#btnNovaFamiliaEditor");
  if ($btnNovaFamilia) {
    $btnNovaFamilia.addEventListener("click", async () => {
      const saved = await abrirModalFamiliaForm(null);
      if (!saved) return;
      if (typeof saved === "boolean") return;
      closeModal();
      try { familias = await api.listarFamilias(); } catch { familias = []; }
      const alvo = saved.id || Number($app.querySelector<HTMLSelectElement>("#eFamilia")!.value);
      $app.querySelector<HTMLSelectElement>("#eFamilia")!.innerHTML = familias.map((f) =>
        `<option value="${f.id}" ${f.id === alvo ? "selected" : ""}>${escapeHtml(f.nome)}</option>`
      ).join("");
      const selecionada = familias.some((f) => f.id === alvo) ? alvo : familias[0] ? familias[0].id : null;
      if (selecionada) {
        $app.querySelector<HTMLSelectElement>("#eFamilia")!.value = String(selecionada);
        carregarAtributosFamilia(selecionada, null);
        renderAtributos($app);
        renderVariantes($app);
      }
    });
  }

  renderAtributos($app);
  renderVariantes($app);

  const $eCategoria = $app.querySelector<HTMLInputElement>("#eCategoria");
  if ($eCategoria) {
    atualizarSubsugestoes($eCategoria.value.trim());
    atualizarPadraoText($app);
    $eCategoria.addEventListener("input", () => {
      atualizarSubsugestoes($eCategoria.value.trim());
      atualizarPadraoText($app);
    });
  }

  const $btnMontarPadrao = $app.querySelector<HTMLElement>("#btnMontarPadrao");
  if ($btnMontarPadrao) {
    $btnMontarPadrao.onclick = () => montarNomePadrao($app);
  }

  if (produto) {
    bindFornecedor($app, produto);
  }

  const $abcRecap = $app.querySelector("#eAbcRecap");
  if ($abcRecap && produto) ($abcRecap as HTMLElement).innerHTML = abcRecapHtml(produto);

  $app.querySelector("#eVariantes")!.addEventListener("input", (e) => {
    const t = e.target as HTMLInputElement;
    if (!t.dataset.field) return;
    const idx = Number(t.dataset.i);
    if (variantes[idx]) {
      const field = t.dataset.field;
      if (field === "sku") variantes[idx].sku = t.value;
      else if (field === "ean") variantes[idx].ean = t.value;
      else if (field === "preco") variantes[idx].preco = t.value;
      else if (field === "prom") variantes[idx].prom = t.value;
    }
  });

  $app.querySelector<HTMLElement>("#btnGerar")!.onclick = () => gerarVariacoes($app);

  $app.querySelector<HTMLElement>("#btnSalvar")!.onclick = () => void salvar($app, produto);

  if (produto) {
    bindImagens($app, produto);
  }
}

// ---------------- Padrão de nomenclatura de fábrica (guia suave) ----------------

const PADRAO_ATTRS = [
  "bitola", "tensao", "tensão", "capacidade", "potencia", "potência",
  "vazao", "vazão", "diametro", "diâmetro", "material", "cor",
  "espessura", "comprimento", "tamanho", "medida", "rolo", "voltagem",
];
const CA_RE = /(^|[^a-z0-9])(n\s?[º°]?\s?ca|ca|certificado|aprovacao)([^a-z0-9]|$)/i;

function normalize(str: string): string {
  return String(str || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function ehAttrPadrao(nome: string): boolean {
  const n = normalize(nome);
  if (CA_RE.test(nome)) return true;
  return PADRAO_ATTRS.some((k) => n.includes(k));
}

function atualizarPadraoText($app: HTMLElement): void {
  const $txt = $app.querySelector("#ePadraoText");
  if (!$txt) return;
  const cat = normalize($app.querySelector<HTMLInputElement>("#eCategoria")!.value.trim());
  let html = "Padrão: <em>Item</em> + <em>Características</em> (bitola, tensão, CA) + <em>Marca</em>.";
  if (cat.includes("epi")) {
    html = "Padrão EPI: <em>Item</em> + <em>Material/Tamanho</em> + <em>Nº CA</em> + <em>Marca</em>.";
  } else if (cat.includes("cabo") || cat.includes("fio")) {
    html = "Padrão de cabos: <em>Item</em> + <em>Bitola (mm²)</em> + <em>Tensão</em> + <em>Norma/Marca</em>.";
  }
  ($txt as HTMLElement).innerHTML = html;
}

function montarNomePadrao($app: HTMLElement): void {
  const base = $app.querySelector<HTMLInputElement>("#eNome")!.value.trim();
  const specs = atributos
    .filter((a) => ehAttrPadrao(a.nome))
    .map((a) => [...(valores[a.id] || [])].join("/"))
    .filter(Boolean);
  const marca = $app.querySelector<HTMLInputElement>("#eMarca")!.value.trim();
  const montado = [base, ...specs, marca].filter(Boolean).join(" ");
  $app.querySelector<HTMLInputElement>("#eNome")!.value = montado;
  if (!montado) {
    toast("Informe o nome base ou selecione valores de atributos para montar.", "error");
  } else {
    toast("Nome montado pelo padrão da família. Ajuste se necessário.", "success");
  }
}

// ---------------- códigos por fornecedor ----------------

async function carregarFornecedores(): Promise<void> {
  if (fornecedores.length) return;
  try { fornecedores = await api.listarFornecedores(true); } catch { fornecedores = []; }
}

function bindFornecedor($app: HTMLElement, produto: ProdutoCadastro): void {
  const $select = $app.querySelector<HTMLSelectElement>("#fvFornecedor");
  if (!$select) return;
  void carregarFornecedores().then(() => {
    $select.innerHTML = `<option value="">Selecione o fornecedor…</option>` +
      fornecedores.map((f) => `<option value="${f.id}">${escapeHtml(f.nome)}</option>`).join("");
  });
  $select.addEventListener("change", () => renderFornecedor($app, produto));
  $app.querySelector<HTMLElement>("#btnSalvarFornecedor")!.onclick = () => void salvarFornecedor($app, produto);
  renderFornecedor($app, produto);
}

function fornecedorMap(produto: ProdutoCadastro, fornecedorId: number): Record<number, FornecedorVariante> {
  const map: Record<number, FornecedorVariante> = {};
  (produto.fornecedor_variantes || [])
    .filter((r) => r.fornecedor_id === fornecedorId)
    .forEach((r) => { map[r.variante_id] = r; });
  return map;
}

function renderFornecedor($app: HTMLElement, produto: ProdutoCadastro): void {
  const $grid = $app.querySelector<HTMLElement>("#fvGrid");
  const $select = $app.querySelector<HTMLSelectElement>("#fvFornecedor");
  if (!$grid || !$select) return;
  const fornecedorId = Number($select.value);
  if (!fornecedorId) { $grid.innerHTML = ""; return; }
  const mapa = fornecedorMap(produto, fornecedorId);
  const rows = variantes.map((v, idx) => {
    const label = atributos.map((a) => v.valores[String(a.id)]).filter(Boolean).join(" · ") || `Variação ${idx + 1}`;
    const key = `${fornecedorId}:${idx}`;
    const saved = v.id != null ? mapa[v.id] : undefined;
    fornecedorEdits[key] = fornecedorEdits[key] || {
      codigo: saved ? saved.codigo_fornecedor : "",
      unidade: saved ? saved.unidade_compra : "",
      fator: saved ? saved.fator_conversao ?? "" : "",
      descricao: saved ? saved.descricao_fornecedor : "",
    };
    const e = fornecedorEdits[key];
    return `
      <tr>
        <td class="fv-variacao" title="${escapeHtml(label)}">${escapeHtml(label)}${v.sku ? ` <span style="color:var(--erp-ink-soft);font-weight:400;">· ${escapeHtml(v.sku)}</span>` : ""}</td>
        <td><input type="text" data-k="${key}" data-f="codigo" placeholder="Código do fornecedor" value="${escapeHtml(e.codigo)}"></td>
        <td><input type="text" data-k="${key}" data-f="unidade" placeholder="Ex.: CX, RL, PC" value="${escapeHtml(e.unidade)}"></td>
        <td><input type="number" min="0" step="0.01" data-k="${key}" data-f="fator" placeholder="1" value="${escapeHtml(String(e.fator !== "" && e.fator != null ? e.fator : ""))}"></td>
      </tr>`;
  }).join("");
  if (!variantes.length) {
    $grid.innerHTML = `<p class="vt-supplier-empty">Gere as variações primeiro para associar os códigos.</p>`;
    return;
  }
  $grid.innerHTML = `
    <table class="vt-supplier-table">
      <thead><tr><th class="fv-c-variacao">Variação</th><th>Código do fornecedor</th><th>Unid. compra</th><th>Fator conv.</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  $grid.querySelectorAll<HTMLInputElement>("input[data-k]").forEach((i) => {
    i.oninput = () => {
      const key = i.dataset.k;
      if (!key) return;
      fornecedorEdits[key] = fornecedorEdits[key] || { ...FORN_EDIT_VAZIO };
      const field = i.dataset.f as keyof FornecedorEdit;
      fornecedorEdits[key][field] = i.value;
    };
  });
}

async function salvarFornecedor($app: HTMLElement, produto: ProdutoCadastro): Promise<void> {
  const fornecedorId = Number($app.querySelector<HTMLSelectElement>("#fvFornecedor")!.value);
  if (!fornecedorId) { toast("Selecione o fornecedor", "error"); return; }
  const itens: FornecedorVariantePayload[] = variantes.map((v, idx) => {
    const e = fornecedorEdits[`${fornecedorId}:${idx}`] || FORN_EDIT_VAZIO;
    return {
      variante_id: v.id ?? 0,
      codigo_fornecedor: e.codigo || "",
      descricao_fornecedor: e.descricao || "",
      unidade_compra: e.unidade || "",
      fator_conversao: e.fator !== "" && e.fator != null ? Number(e.fator) : 1,
    };
  });
  try {
    const res = await api.salvarFornecedorVariantes(produto.id, fornecedorId, itens);
    produto.fornecedor_variantes = res.mapping;
    toast(`Códigos salvos para ${fornecedores.find((f) => f.id === fornecedorId)?.nome || "o fornecedor"}`, "success");
    renderFornecedor($app, produto);
  } catch (e) {
    toast("Erro ao salvar códigos: " + (e as Error).message, "error");
  }
}

function renderAtributos($app: HTMLElement): void {
  const $wrap = $app.querySelector<HTMLElement>("#eAtributos");
  if (!$wrap) return;
  if (!atributos.length) {
    $wrap.innerHTML = `<p style="font-size:13px;color:var(--ink-soft);">Essa família não tem atributos. Edite a família para adicioná-los.</p>`;
    return;
  }
  $wrap.innerHTML = atributos.map(attrBlockHtml).join("");
  $wrap.querySelectorAll<HTMLInputElement>(".chip input").forEach((i) => {
    i.onchange = (ev) => {
      const input = ev.target as HTMLInputElement;
      const attrId = Number(input.dataset.attr);
      const set = valores[attrId];
      if (!set) return;
      if (input.checked) set.add(input.value); else set.delete(input.value);
      renderAtributos($app);
    };
  });
  $wrap.querySelectorAll<HTMLElement>(".attr-add").forEach((box) => {
    const input = box.querySelector<HTMLInputElement>("input");
    const button = box.querySelector<HTMLButtonElement>("button");
    if (!input || !button) return;
    button.onclick = () => {
      const attrId = Number(input.dataset.attr);
      const val = input.value.trim();
      if (!val) return;
      if (!valores[attrId]) valores[attrId] = new Set();
      valores[attrId].add(val);
      input.value = "";
      renderAtributos($app);
    };
    input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const val = input.value.trim();
      if (!val) return;
      const attrId = Number(input.dataset.attr);
      if (!valores[attrId]) valores[attrId] = new Set();
      valores[attrId].add(val);
      input.value = "";
      renderAtributos($app);
    });
  });
}

function attrBlockHtml(a: Atributo): string {
  const set = valores[a.id];
  const opts = a.tipo === "lista" ? [...a.opcoes] : [];
  const custom = [...(set || [])].filter((v) => !opts.includes(v));
  const display = [...opts, ...custom];
  const marker = (v: string) => `<span class="chip-check" aria-hidden="true">${set && set.has(v) ? "✓" : ""}</span>`;
  const titular = () => `
    <span class="attr-title attr-title-obr">${escapeHtml(a.nome)}
      ${a.obrigatorio ? `<span class="obr-badge" title="Atributo obrigatório para produtos desta família">* obrigatório</span>` : ""}
    </span>`;
  if (!display.length && a.tipo === "livre") {
    return `
      <div class="attr-block ${a.obrigatorio ? "has-obrigatorio" : ""}">
        <div class="attr-head">${titular()}</div>
        <div class="attr-add">
          <input type="text" data-attr="${a.id}" placeholder="Digite o valor e pressione Enter…">
          <button type="button" class="btn btn--ghost btn--sm">Adicionar</button>
        </div>
      </div>`;
  }
  return `
    <div class="attr-block ${a.obrigatorio ? "has-obrigatorio" : ""}">
      <div class="attr-head">${titular()}</div>
      <div class="chip-group">${display.map((v) => `
        <label class="chip ${set && set.has(v) ? "is-on" : ""}">
          <input type="checkbox" data-attr="${a.id}" value="${escapeHtml(v)}" ${set && set.has(v) ? "checked" : ""}>
          ${marker(v)}${escapeHtml(v)}
        </label>`).join("")}
      </div>
      <div class="attr-add">
        <input type="text" data-attr="${a.id}" placeholder="Adicionar valor…">
        <button type="button" class="btn btn--ghost btn--sm">Adicionar</button>
      </div>
    </div>`;
}

// ---------------- variações (combinações) ----------------

function gerarVariacoes($app: HTMLElement): void {
  const keys = atributos.map((a) => a.id);
  const vazios = atributos.filter((a) => !valores[a.id] || valores[a.id].size === 0);
  if (vazios.length) {
    toast(`Selecione ao menos um valor para: ${vazios.map((a) => a.nome).join(", ")}`, "error");
    return;
  }
  const arrays = keys.map((k) => [...(valores[k] || [])]);
  const combos = cartesiano(arrays);
  const existentes: Record<string, VarianteLocal> = {};
  variantes.forEach((v) => { existentes[JSON.stringify(v.valores)] = v; });
  variantes = combos.map((vals) => {
    const attr: Record<string, string> = {};
    keys.forEach((k, j) => { attr[String(k)] = vals[j]; });
    const prev = existentes[JSON.stringify(attr)];
    return {
      id: prev ? prev.id : undefined,
      sku: prev ? prev.sku : "",
      ean: prev ? prev.ean : "",
      preco: prev ? prev.preco : "",
      prom: prev ? prev.prom : "",
      valores: attr,
    };
  });
  renderVariantes($app);
  toast(`${variantes.length} variação(ões) gerada(s)`, "success");
}

function cartesiano(arrays: string[][]): string[][] {
  return arrays.reduce((acc, cur) => acc.flatMap((a) => cur.map((c) => [...a, c])), [[]] as string[][]);
}

function renderVariantes($app: HTMLElement): void {
  const $wrap = $app.querySelector<HTMLElement>("#eVariantes");
  const $hint = $app.querySelector<HTMLElement>("#eVariantesHint");
  if (!$wrap) return;
  if (!atributos.length) {
    if ($hint) $hint.textContent = "";
    $wrap.innerHTML = `<p class="erp-empty">Selecione uma família com atributos para gerar variações.</p>`;
    return;
  }
  if (!variantes.length) {
    if ($hint) $hint.textContent = "Selecione os valores dos atributos e clique em \u201CGerar Variações\u201D.";
    $wrap.innerHTML = "";
    return;
  }
  if ($hint) $hint.textContent = `${variantes.length} variação(ões) · atributos: ${atributos.map((a) => a.nome).join(" · ")}. Edite diretamente nas células (SKU, EAN, Preço, Promo).`;
  const rows = variantes.map((v, idx) => {
    const label = atributos.map((a) => v.valores[String(a.id)]).filter(Boolean).join(" · ") || "—";
    return `
    <tr class="${idx % 2 ? "is-zebra" : ""}">
      <td class="vt-variacao" title="${escapeHtml(label)}">${escapeHtml(label)}</td>
      <td><input data-i="${idx}" data-field="sku" type="text" placeholder="SKU" value="${escapeHtml(v.sku)}"></td>
      <td><input data-i="${idx}" data-field="ean" type="text" placeholder="EAN" value="${escapeHtml(v.ean)}"></td>
      <td><input data-i="${idx}" data-field="preco" type="number" min="0" step="0.01" placeholder="R$" value="${escapeHtml(v.preco !== "" && v.preco != null ? String(v.preco) : "")}"></td>
      <td><input data-i="${idx}" data-field="prom" type="number" min="0" step="0.01" placeholder="Promo" value="${escapeHtml(v.prom !== "" && v.prom != null ? String(v.prom) : "")}"></td>
      <td class="vt-del"><button type="button" class="icon-btn" data-rm="${idx}" title="Remover variação">×</button></td>
    </tr>`;
  }).join("");
  $wrap.innerHTML = `
    <table class="vt-grid">
      <thead>
        <tr><th class="vt-c-variacao">Variação</th><th>SKU</th><th>EAN</th><th>Preço</th><th>Promo.</th><th class="vt-c-del"></th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  $wrap.querySelectorAll<HTMLElement>("[data-rm]").forEach((b) => {
    b.onclick = () => { variantes.splice(Number(b.dataset.rm), 1); renderVariantes($app); };
  });
}

// ---------------- salvar ----------------

function abcRecapHtml(p: ProdutoCadastro): string {
  const chips = (nome: string, val: string | number | null | undefined, cor: string) => val
    ? `<span class="abc-chip" style="background:${cor};color:#fff;">${escapeHtml(nome)}: <strong>${escapeHtml(String(val))}</strong></span>`
    : "";
  const classe = p.classe_abc || "—";
  const corClasse = classe === "A" ? "#2f6df6" : classe === "B" ? "#e8a000" : classe === "C" ? "#9aa4b2" : "transparent";
  const emLinha = p.em_linha == null ? "" : (p.em_linha ? "No rolar" : "Fora do rolar");
  const corLinha = p.em_linha == null ? "" : (p.em_linha ? "#1c9d74" : "#d04848");
  return `
    <div style="display:flex;flex-wrap:wrap;gap:8px;">
      <span class="abc-chip" style="background:${corClasse};color:#fff;${classe === "—" ? "background:#e7ebf0;color:#667;" : ""}">Classe: <strong>${escapeHtml(String(classe))}</strong></span>
      ${emLinha !== "" ? `<span class="abc-chip" style="background:${corLinha};color:#fff;">${emLinha}</span>` : ""}
      ${chips("Linha", p.linha_produto, "#5b6472")}
      ${chips("Margem", p.margem_lucro_estimada != null ? (p.margem_lucro_estimada * 100).toFixed(0) + "%" : "", "#8a5bd8")}
      ${chips("Giro", p.giro_esperado_mercado != null ? p.giro_esperado_mercado.toFixed(2) : "", "#0f7bd8")}
      ${chips("Valor", p.valor_agregado, "#0f87a8")}
      ${chips("Lucro est.", p.lucro_total_estimado != null ? fmtMoney(p.lucro_total_estimado) : "", "#1c9d74")}
    </div>`;
}

async function salvar($app: HTMLElement, produto: ProdutoCadastro | null): Promise<void> {
  const familia_id = Number($app.querySelector<HTMLSelectElement>("#eFamilia")!.value);
  const nome = $app.querySelector<HTMLInputElement>("#eNome")!.value.trim();
  if (!familia_id) { toast("Selecione a família", "error"); return; }
  if (!nome) { toast("Informe o nome base do produto", "error"); return; }

  // -- validações de atributos obrigatórios + CA (EPI) --
  const semsValor = atributos.filter(
    (a) => a.obrigatorio && (!valores[a.id] || valores[a.id].size === 0)
  );
  if (semsValor.length) {
    toast("Preencha os atributos obrigatórios: " + semsValor.map((a) => a.nome).join(", "), "error");
    $app.querySelector<HTMLElement>('.erp-tab[data-tab="atributos"]')!.click();
    return;
  }
  const caAttrs = atributos.filter((a) => CA_RE.test(a.nome));
  for (const a of caAttrs) {
    for (const v of (valores[a.id] || [])) {
      if (!/^[\d.\s]+$/.test(String(v).trim())) {
        toast(`O atributo "${a.nome}" deve ser um número de CA válido (ex.: 12345 ou 12.345).`, "error");
        $app.querySelector<HTMLElement>('.erp-tab[data-tab="atributos"]')!.click();
        return;
      }
    }
  }

  const payload: ProdutoCadastroPayload = {
    familia_id,
    nome,
    marca: $app.querySelector<HTMLInputElement>("#eMarca")!.value.trim(),
    descricao: $app.querySelector<HTMLInputElement>("#eDesc")!.value.trim(),
    termos_busca: $app.querySelector<HTMLInputElement>("#eTermosBusca")!.value.trim(),
    categoria: $app.querySelector<HTMLInputElement>("#eCategoria")!.value.trim(),
    subcategoria: $app.querySelector<HTMLInputElement>("#eSubcategoria")!.value.trim(),
    variantes: variantes.map((v) => ({
      id: v.id,
      sku: v.sku || "",
      ean: v.ean || "",
      preco: v.preco !== "" && v.preco != null ? Number(v.preco) : 0,
      preco_promocional: v.prom !== "" && v.prom != null ? Number(v.prom) : null,
      observacao: "",
      atributos: v.valores,
    })),
  };
  try {
    let id = produto ? produto.id : null;
    if (produto) await api.atualizarProdutoCadastro(produto.id, payload);
    else {
      const res = await api.criarProdutoCadastro(payload);
      id = res.id;
    }
    toast("Produto salvo", "success");
    if (produto) {
      location.hash = `#/produtos/${produto.id}`;
    } else {
      location.hash = `#/produtos/${id}`;
    }
  } catch (e) {
    toast("Erro ao salvar: " + (e as Error).message, "error");
  }
}

// ---------------- imagens ----------------

function bindImagens($app: HTMLElement, produto: ProdutoCadastro): void {
  const renderImagens = () => {
    const $grid = $app.querySelector<HTMLElement>("#imgGrid");
    if (!$grid) return;
    const imgs = produto.imagens || [];
    if (!imgs.length) {
      $grid.innerHTML = `<p style="font-size:13px;color:var(--ink-soft);">Nenhuma imagem. Envie arquivos ou informe a URL de uma página do produto.</p>`;
      return;
    }
    $grid.innerHTML = imgs.map((im, i) => `
      <div class="img-cell ${i === 0 ? "is-capa" : ""}">
        <img src="${escapeHtml(im.url)}" loading="lazy" alt="">
        ${i === 0 ? `<span class="img-capa-badge">Capa</span>` : ""}
        ${i > 0 ? `<button class="img-capa-btn" data-capa="${im.id}" title="Definir como imagem de capa">★</button>` : ""}
        <button class="img-remove" data-img="${im.id}" title="Excluir imagem">×</button>
      </div>`).join("");
    $grid.querySelectorAll<HTMLElement>(".img-remove").forEach((b) => {
      b.onclick = async () => {
        try {
          await api.excluirImagem(Number(b.dataset.img));
          produto.imagens = produto.imagens.filter((x) => x.id !== Number(b.dataset.img));
          renderImagens();
        } catch (e) { toast("Erro ao excluir imagem: " + (e as Error).message, "error"); }
      };
    });
    $grid.querySelectorAll<HTMLElement>(".img-capa-btn").forEach((b) => {
      b.onclick = async () => {
        (b as HTMLButtonElement).disabled = true;
        try {
          await api.definirCapaImagem(produto.id, Number(b.dataset.capa));
          produto = await api.detalharProdutoCadastro(produto.id);
          renderImagens();
          toast("Imagem de capa atualizada", "success");
        } catch (e) {
          toast("Erro ao definir capa: " + (e as Error).message, "error");
        } finally {
          (b as HTMLButtonElement).disabled = false;
        }
      };
    });
  };

  $app.querySelector<HTMLInputElement>("#imgUpload")!.addEventListener("change", async (e) => {
    const files = (e.target as HTMLInputElement).files;
    if (!files || !files.length) return;
    const count = files.length;
    const fd = new FormData();
    for (let i = 0; i < files.length; i++) fd.append("files", files[i]);
    try {
      await api.enviarImagensProduto(produto.id, fd);
      produto = await api.detalharProdutoCadastro(produto.id);
      renderImagens();
      toast(`${count} imagem(ns) enviada(s)`, "success");
    } catch (err) {
      toast("Erro no upload: " + (err as Error).message, "error");
    }
    (e.target as HTMLInputElement).value = "";
  });

  $app.querySelector<HTMLElement>("#btnBaixarUrl")!.onclick = async () => {
    const url = $app.querySelector<HTMLInputElement>("#imgUrl")!.value.trim();
    if (!url) { toast("Informe a URL", "error"); return; }
    const $btn = $app.querySelector<HTMLButtonElement>("#btnBaixarUrl")!;
    $btn.disabled = true;
    $btn.textContent = "Baixando…";
    try {
      const res = await api.baixarImagensUrl(produto.id, url);
      produto = await api.detalharProdutoCadastro(produto.id);
      renderImagens();
      toast(`${res.total} imagem(ns) baixada(s)`, "success");
      if (res.erros && res.erros.length) {
        toast(`Erros: ${res.erros.slice(0, 3).join(" | ")}`, "error");
      }
    } catch (err) {
      toast("Erro ao baixar: " + (err as Error).message, "error");
    } finally {
      $btn.disabled = false;
      $btn.textContent = "Baixar da internet";
    }
  };

  renderImagens();
}

// ===================================================================