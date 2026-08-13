// pages/compras.ts — fluxo de compra em tela única (NFC).
// Port 1:1 de catalog_server/static/page_compras.js.
// Etapas: 1 Lista ➔ 2 Cotando ➔ 3 Comparando ➔ 4 Pedido Gerado.

import {
  api,
  type CotacaoComprasPayload,
  type CotacaoFornecedor,
  type Fornecedor,
  type Invite,
  type MatrizComparacao,
  type MatrizItem,
} from "../api/client";
import { escapeHtml, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";

const KEY_DRAFT = "compras_draft";
const KEY_COT = "compras_cotacao";
const KEY_PESOS = "compras_pesos_recomendado";

interface Pesos {
  preco: number;
  prazo: number;
  pagamento: number;
}

const PESOS_PADRAO: Pesos = { preco: 50, prazo: 30, pagamento: 20 };

function carregarPesos(): Pesos {
  try {
    const raw = sessionStorage.getItem(KEY_PESOS);
    if (!raw) return { ...PESOS_PADRAO };
    const p = JSON.parse(raw) as Partial<Pesos>;
    return {
      preco: p.preco ?? PESOS_PADRAO.preco,
      prazo: p.prazo ?? PESOS_PADRAO.prazo,
      pagamento: p.pagamento ?? PESOS_PADRAO.pagamento,
    };
  } catch {
    return { ...PESOS_PADRAO };
  }
}

function salvarPesos(p: Pesos): void {
  sessionStorage.setItem(KEY_PESOS, JSON.stringify(p));
}

/**
 * Para cada item, calcula qual fornecedor tem a melhor pontuação combinando
 * preço líquido, prazo de entrega e condição de pagamento do fornecedor,
 * conforme os pesos informados pelo comprador (0-100 cada, normalizados
 * internamente). Quanto menor o preço/prazo e maior o prazo de pagamento
 * (mais dias para pagar), melhor a pontuação.
 */
function calcularRecomendados(
  itens: MatrizItem[],
  fornecedores: CotacaoFornecedor[],
  pesos: Pesos
): Map<number, number> {
  const diasPagto = new Map<number, number | null>();
  fornecedores.forEach((f) => diasPagto.set(f.fornecedor_id, f.condicao_pagamento_dias ?? null));

  const somaPesos = Math.max(1, pesos.preco + pesos.prazo + pesos.pagamento);
  const wPreco = pesos.preco / somaPesos;
  const wPrazo = pesos.prazo / somaPesos;
  const wPagto = pesos.pagamento / somaPesos;

  const resultado = new Map<number, number>();

  for (const item of itens) {
    const candidatos = Object.entries(item.precos).filter(
      ([, pr]) => pr.disponivel && pr.preco_liquido > 0
    );
    if (candidatos.length === 0) continue;

    const maxPreco = Math.max(...candidatos.map(([, pr]) => pr.preco_liquido));
    const prazosValidos = candidatos.map(([, pr]) => pr.prazo).filter((p): p is number => p != null);
    const maxPrazo = prazosValidos.length ? Math.max(...prazosValidos) : 0;
    const diasValidos = candidatos
      .map(([fid]) => diasPagto.get(Number(fid)))
      .filter((d): d is number => d != null);
    const maxDias = diasValidos.length ? Math.max(...diasValidos) : 0;

    let melhorFid: number | null = null;
    let melhorScore = -Infinity;

    for (const [fid, pr] of candidatos) {
      const normPreco = maxPreco > 0 ? pr.preco_liquido / maxPreco : 0;
      const normPrazo = maxPrazo > 0 ? (pr.prazo ?? maxPrazo) / maxPrazo : 0;
      const dias = diasPagto.get(Number(fid)) ?? 0;
      const normDias = maxDias > 0 ? dias / maxDias : 0;

      const score = wPreco * (1 - normPreco) + wPrazo * (1 - normPrazo) + wPagto * normDias;
      if (score > melhorScore) {
        melhorScore = score;
        melhorFid = Number(fid);
      }
    }
    if (melhorFid != null) resultado.set(item.cotacao_item_id, melhorFid);
  }

  return resultado;
}

// ---------------------------------------------------------------- helpers

interface ItemDraft {
  produto_id: number;
  quantidade: number;
  name?: string;
  category?: string;
}

interface FornecedorDraft {
  id: number | null;
  nome?: string;
  whatsapp?: string;
  email?: string;
}

interface Draft {
  apelido: string;
  comprador: string;
  data_limite: string;
  agrupar: boolean;
  itens: ItemDraft[];
  fornecedores: FornecedorDraft[];
}

// Card retornado por /api/produtos (agrupado=1): é a forma de catálogo usada
// na busca desta página (sempre tem `group`).
interface CardBusca {
  group: boolean;
  id: number;
  name: string;
  sku: string;
  brand?: string;
  category?: string;
  price: number;
  price_min?: number;
  imagem_url?: string | null;
  variants?: { id: number }[];
}

interface CategoriaOption {
  nome: string;
}

// O módulo PageIA (importer de resposta IA) ainda não foi portado para Vite/TS
// — fica plugável aqui; quando migrado, a etapa 3 deve chamar registrarImportadorIA().
interface ImportarIAOpts {
  cotacaoId: number;
  fornecedores: CotacaoFornecedor[];
  titulo: string;
  onAplicado: () => void;
}

let importarIa: ((opts: ImportarIAOpts) => void) | null = null;

export function registrarImportadorIA(fn: (opts: ImportarIAOpts) => void): void {
  importarIa = fn;
}

const S: { etapa: number; cotacaoId: number | null; logica: string; draft: Draft } = {
  etapa: 1,
  cotacaoId: null,
  logica: "fracionado",
  draft: novoDraft(),
};

const ETAPAS: { n: number; nome: string }[] = [
  { n: 1, nome: "Lista" },
  { n: 2, nome: "Cotando" },
  { n: 3, nome: "Comparando" },
  { n: 4, nome: "Pedido Gerado" },
];

function novoDraft(): Draft {
  return {
    apelido: "",
    comprador: "",
    data_limite: "",
    agrupar: false,
    itens: [],
    fornecedores: [],
  };
}

function esc(s: unknown): string {
  return escapeHtml(s == null ? "" : s);
}

function salvar(): void {
  sessionStorage.setItem(KEY_DRAFT, JSON.stringify(S.draft || {}));
  if (S.cotacaoId) sessionStorage.setItem(KEY_COT, String(S.cotacaoId));
}

function stepper(): string {
  return (
    '<div class="cpr-stepper">' +
    ETAPAS.map(
      (e) =>
        `<div class="cpr-step${e.n === S.etapa ? " is-cur" : ""}${e.n < S.etapa ? " is-done" : ""}">
         <span class="cpr-num">${e.n}</span><span class="cpr-nome">${e.nome}</span>
       </div>`
    ).join('<span class="cpr-link"></span>') +
    `<span class="cpr-status cpr-status-${S.etapa}"></span></div>`
  );
}

function barra(msg: string): string {
  return `<div class="cpr-empty"><div class="cpr-spin"></div><p>${esc(msg)}</p></div>`;
}

function appScope(el: HTMLElement): HTMLElement {
  return (el.closest("#app") as HTMLElement | null) ?? el;
}

// ---------------------------------------------------------------- render

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `
    <div class="page-head">
      <div><h1 class="page-title">Comprar</h1>
      <p class="page-sub">Monte a lista, cote com os fornecedores e gere o pedido em uma tela só.</p></div>
      <button class="btn btn--ghost" id="cprNova">＋ Nova compra</button>
    </div>
    <div id="cprStepper"></div>
    <div id="cprBody"></div>`;
  $app.querySelector("#cprNova")!.addEventListener("click", () => {
    sessionStorage.removeItem(KEY_COT);
    S.cotacaoId = null;
    S.draft = novoDraft();
    salvar();
    S.etapa = 1;
    desenhar($app);
  });
  await init($app);
}

async function init($app: HTMLElement): Promise<void> {
  try {
    S.draft =
      (JSON.parse(sessionStorage.getItem(KEY_DRAFT) || "null") as Draft | null) || novoDraft();
  } catch {
    S.draft = novoDraft();
  }
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
async function resume($app: HTMLElement): Promise<void> {
  try {
    const m = await api.compararCotacao(S.cotacaoId!);
    const status = m.cotacao.status;
    if (status === "finalizada") S.etapa = 4;
    else if (status === "analise") S.etapa = 3;
    else S.etapa = 3; // pendente mas já enviada: ver matriz
    desenhar($app);
  } catch {
    sessionStorage.removeItem(KEY_COT);
    S.cotacaoId = null;
    S.etapa = 1;
    desenhar($app);
  }
}

function desenhar($app: HTMLElement): void {
  $app.querySelector("#cprStepper")!.innerHTML = stepper();
  const body = $app.querySelector<HTMLElement>("#cprBody");
  if (!body) return;
  const fns: Record<number, (b: HTMLElement) => Promise<void> | void> = {
    1: etapaLista,
    2: etapaCotando,
    3: etapaComparando,
    4: etapaPedidos,
  };
  const fn = fns[S.etapa];
  if (fn) void fn(body);
}

// ============================================================ ETAPA 1

async function etapaLista(body: HTMLElement): Promise<void> {
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

async function preencherCategorias(body: HTMLElement): Promise<void> {
  try {
    const cats = (await api.listarCategorias()) as unknown as CategoriaOption[];
    const sel = body.querySelector("#cprCat");
    if (!sel) return;
    (cats || []).forEach((c) =>
      sel.insertAdjacentHTML(
        "beforeend",
        `<option value="${esc(c.nome)}">${esc(c.nome)}</option>`
      )
    );
  } catch {
    /* filtro de grupos é opcional */
  }
}

function vincularBusca(body: HTMLElement): void {
  const q = body.querySelector<HTMLInputElement>("#cprQ")!;
  const cat = body.querySelector<HTMLSelectElement>("#cprCat")!;
  let timer: ReturnType<typeof setTimeout> | undefined;
  function buscar(): void {
    clearTimeout(timer);
    timer = setTimeout(() => {
      api
        .listarProdutos({ q: q.value.trim(), categoria: cat.value, limit: 12, agrupado: 1 })
        .then((r) => desenharResultado(body, (r.items || []) as unknown as CardBusca[]))
        .catch((e) => {
          const box = body.querySelector("#cprResult");
          if (box) box.innerHTML = `<p class="cpr-erro">${esc((e as Error).message)}</p>`;
        });
    }, 300);
  }
  q.addEventListener("input", buscar);
  cat.addEventListener("change", buscar);
  body.querySelector<HTMLInputElement>("#cprAgrupar")!.addEventListener("change", (e) => {
    S.draft.agrupar = (e.target as HTMLInputElement).checked;
    salvar();
  });
}

function gpFamilia(itens: ItemDraft[]): string {
  const it = itens[0];
  return it ? it.category || "" : "";
}

function desenharResultado(body: HTMLElement, itens: CardBusca[]): void {
  const box = body.querySelector<HTMLElement>("#cprResult");
  if (!box) return;
  if (!itens.length) {
    box.innerHTML = `<p class="cpr-vazio">Nenhum produto encontrado.</p>`;
    return;
  }
  box.innerHTML = itens
    .map((p) => {
      const vid = p.group && p.variants && p.variants[0] ? p.variants[0].id : p.id;
      return `
      <div class="cpr-card">
        <img src="${esc(p.imagem_url || "")}" onerror="this.style.visibility=&#39;hidden&#39;">
        <div class="cpr-card-info">
          <div class="cpr-card-nome">${esc(p.name)}</div>
          <div class="cpr-card-meta">${esc(p.sku || "")}${p.brand ? " · " + esc(p.brand) : ""}${p.category ? " · " + esc(p.category) : ""}</div>
          <div class="cpr-card-preco">${fmtMoney(p.group ? p.price_min : p.price)}</div>
        </div>
        <button class="btn btn--sm btn--accent" data-add="${vid}">Adicionar</button>
      </div>`;
    })
    .join("");
  box.querySelectorAll<HTMLElement>("[data-add]").forEach((b) =>
    b.addEventListener("click", () => adicionar(body, Number(b.dataset.add)))
  );
}

function adicionar(body: HTMLElement, produtoId: number): void {
  // precisa do produto para categoria; recupera do resultado atual
  const box = body.querySelector<HTMLElement>("#cprResult");
  if (!box) return;
  const card = box.querySelector<HTMLElement>(`[data-add="${produtoId}"]`);
  const nome =
    card?.closest(".cpr-card")?.querySelector(".cpr-card-nome")?.textContent?.trim() ?? "";
  const exist = S.draft.itens.find((i) => i.produto_id === produtoId);
  if (exist) {
    exist.quantidade += 1;
  } else {
    const cat = card ? catDe(card) : "";
    if (S.draft.agrupar && S.draft.itens.length && cat && gpFamilia(S.draft.itens) !== cat) {
      toast("Grupo diferente: ative a opção de não misturar ou remova o item.", "error");
      return;
    }
    S.draft.itens.push({ produto_id: produtoId, quantidade: 1, name: nome, category: cat });
  }
  salvar();
  desenharLista(body);
}

function catDe(card: Element): string {
  const m = card.querySelector(".cpr-card-meta");
  const t = m ? (m.textContent ?? "").split(" · ") : [];
  return t.length ? (t[t.length - 1] ?? "") : "";
}

function desenharLista(body: HTMLElement): void {
  const box = body.querySelector<HTMLElement>("#cprLista");
  body.querySelector<HTMLElement>("#cprNItens")!.textContent = String(S.draft.itens.length);
  if (!box) return;
  if (!S.draft.itens.length) {
    box.innerHTML = `<p class="cpr-vazio">Nenhum item na lista.<br>Use a busca ao lado e clique em "Adicionar".</p>`;
    return;
  }
  const itensBox = S.draft.itens;
  box.innerHTML = itensBox
    .map(
      (it, idx) => `
      <div class="cpr-linha" data-idx="${idx}">
        <span class="cpr-linha-nome">${esc(it.name || "#" + it.produto_id)}</span>
        <input class="cpr-qtd" type="number" min="1" step="1" value="${it.quantidade}" data-idx="${idx}">
        <button class="btn btn--sm btn--ghost cpr-rm" data-idx="${idx}">✕</button>
      </div>`
    )
    .join("");
  // navegação por Enter/Tab para a próxima linha
  box.querySelectorAll<HTMLInputElement>(".cpr-qtd").forEach((inp) => {
    inp.addEventListener("input", () => {
      const it = itensBox[Number(inp.dataset.idx)];
      it.quantidade = Math.max(1, Number(inp.value) || 1);
      salvar();
    });
    inp.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === "Tab") {
        const next = box.querySelector<HTMLInputElement>(
          `.cpr-qtd[data-idx="${Number(inp.dataset.idx) + 1}"]`
        );
        if (next) {
          e.preventDefault();
          next.focus();
          next.select();
        }
      }
    });
  });
  box.querySelectorAll<HTMLElement>(".cpr-rm").forEach((b) =>
    b.addEventListener("click", () => {
      itensBox.splice(Number(b.dataset.idx), 1);
      salvar();
      desenharLista(body);
    })
  );
  body.querySelector<HTMLInputElement>("#cprApelido")!.addEventListener("input", (e) => {
    S.draft.apelido = (e.target as HTMLInputElement).value;
    salvar();
  });
  body.querySelector<HTMLInputElement>("#cprData")!.addEventListener("change", (e) => {
    S.draft.data_limite = (e.target as HTMLInputElement).value;
    salvar();
  });
  const btn = body.querySelector<HTMLButtonElement>("#cprProx1");
  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = "1";
    btn.addEventListener("click", () => {
      if (!S.draft.itens.length) {
        toast("Adicione pelo menos 1 produto.", "error");
        return;
      }
      S.etapa = 2;
      desenhar(appScope(body));
    });
  }
}

// ============================================================ ETAPA 2

async function etapaCotando(body: HTMLElement): Promise<void> {
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
  body.querySelector("#cprDisparar")!.addEventListener("click", () => disparar(body));
}

function desenharMiniLista(body: HTMLElement): void {
  const box = body.querySelector("#cprMiniLista");
  if (!box) return;
  box.innerHTML = S.draft.itens
    .map(
      (it) =>
        `<div class="cpr-mini"><span>${esc(it.name || "#" + it.produto_id)}</span><b>${it.quantidade}</b></div>`
    )
    .join("");
}

async function desenharFornecedores(body: HTMLElement): Promise<void> {
  let fornecedores: Fornecedor[] = [];
  try {
    fornecedores = await api.listarFornecedores(true);
  } catch {
    /* segue com lista vazia */
  }
  S.draft.fornecedores = S.draft.fornecedores.filter((f) => f.id);
  const box = body.querySelector("#cprForn");
  if (!box) return;
  box.innerHTML =
    fornecedores
      .map((f) => {
        const sel = S.draft.fornecedores.some((x) => x.id === f.id);
        return `<label class="cpr-linha cpr-frow">
        <input type="checkbox" data-fid="${f.id}" ${sel ? "checked" : ""}>
        <span>${esc(f.nome)}</span>
        <small>${esc(f.whatsapp || (f.email ? "e-mail" : "sem contato"))}</small>
      </label>`;
      })
      .join("") || `<p class="cpr-vazio">Nenhum fornecedor cadastrado.</p>`;
  box.querySelectorAll<HTMLInputElement>("input[type=checkbox]").forEach((c) =>
    c.addEventListener("change", () => {
      const fid = Number(c.dataset.fid);
      if (c.checked) S.draft.fornecedores.push({ id: fid });
      else S.draft.fornecedores = S.draft.fornecedores.filter((x) => x.id !== fid);
      salvar();
    })
  );
}

function vincularExpress(body: HTMLElement): void {
  const add = body.querySelector("#fxAdd")!;
  add.addEventListener("click", () => {
    const nome = body.querySelector<HTMLInputElement>("#fxNome")!.value.trim();
    if (!nome) {
      toast("Informe o nome do fornecedor.", "error");
      return;
    }
    S.draft.fornecedores.push({
      id: null,
      nome,
      whatsapp: body.querySelector<HTMLInputElement>("#fxWhats")!.value.trim(),
      email: body.querySelector<HTMLInputElement>("#fxEmail")!.value.trim(),
    });
    body.querySelector<HTMLInputElement>("#fxNome")!.value = "";
    body.querySelector<HTMLInputElement>("#fxWhats")!.value = "";
    body.querySelector<HTMLInputElement>("#fxEmail")!.value = "";
    void desenharFornecedores(body);
    toast("Fornecedor rápido adicionado à cotação.");
  });
}

async function disparar(body: HTMLElement): Promise<void> {
  if (!S.draft.fornecedores.length) {
    toast("Convide pelo menos 1 fornecedor.", "error");
    return;
  }
  const btn = body.querySelector<HTMLButtonElement>("#cprDisparar");
  if (btn) {
    btn.disabled = true;
    btn.classList.add("is-loading");
    btn.innerHTML = '<span class="spinner"></span> Enviando…';
  }
  const payload: CotacaoComprasPayload = {
    apelido: S.draft.apelido,
    comprador: S.draft.comprador || "Loja",
    data_limite: S.draft.data_limite,
    itens: S.draft.itens.map((i) => ({ produto_id: i.produto_id, quantidade: i.quantidade })),
    fornecedores: S.draft.fornecedores.map((f) =>
      f.id
        ? { fornecedor_id: f.id }
        : { nome: f.nome ?? "", whatsapp: f.whatsapp ?? "", email: f.email ?? "" }
    ),
  };
  try {
    const r = await api.criarCotacaoCompras(payload);
    S.cotacaoId = r.id;
    S.draft.fornecedores = [];
    sessionStorage.setItem(KEY_COT, String(r.id));
    salvar();
    await mostrarLinks(body, r.invites || []);
  } catch (e) {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("is-loading");
      btn.innerHTML = "Disparar Cotação ➔";
    }
    toast((e as Error).message, "error");
  }
}

async function mostrarLinks(body: HTMLElement, invites: Invite[]): Promise<void> {
  const box = (body.querySelector("#cprBody") ?? body.closest("#app")?.querySelector("#cprBody"))!;
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
  const links = box.querySelector<HTMLElement>("#cprLinks");
  if (links) {
    links.innerHTML = invites
      .map(
        (inv) => `
      <div class="cpr-linkcard">
        <div><b>${esc(inv.nome)}</b><span class="cpr-lk-status">${inv.status === "respondido" ? "✓ respondeu" : "pendente"}</span></div>
        <div class="cpr-lk-acoes">
          ${inv.whatsapp_url ? `<a class="btn btn--wa" target="_blank" rel="noopener" href="${esc(inv.whatsapp_url)}">WhatsApp</a>` : ""}
          ${inv.mailto_url ? `<a class="btn" href="${esc(inv.mailto_url)}">E-mail</a>` : ""}
          <button class="btn" data-copiar="${esc(inv.link)}">Copiar link</button>
        </div>
      </div>`
      )
      .join("");
    links.querySelectorAll<HTMLElement>("[data-copiar]").forEach((b) =>
      b.addEventListener("click", (e) => {
        const url = (e.currentTarget as HTMLElement).dataset.copiar ?? "";
        void navigator.clipboard.writeText(url).then(() => toast("Link copiado!"));
      })
    );
  }
  box.querySelector("#cprVoltarLista")!.addEventListener("click", () => {
    S.etapa = 2;
    desenhar(appScope(body));
  });
  box.querySelector("#cprIrComparar")!.addEventListener("click", () => {
    S.etapa = 3;
    desenhar(appScope(body));
  });
}

// ============================================================ ETAPA 3

async function etapaComparando(body: HTMLElement): Promise<void> {
  body.innerHTML = `<div class="cpr-panel">${barra("Aguardando respostas dos fornecedores…")}</div>`;
  try {
    const m = await api.compararCotacao(S.cotacaoId!);
    if (
      m.cotacao.status !== "analise" &&
      m.cotacao.status !== "finalizada" &&
      !m.fornecedores.some((f) => f.status === "respondido")
    ) {
      body.innerHTML = `
        <div class="cpr-panel cpr-wait">
          <div class="cpr-spin"></div>
          <h3 class="cpr-titulo">Cotação disparada — aguardando respostas</h3>
          <p class="cpr-sub">Quando os fornecedores responderem (ou você apertar o botão), a matriz aparece aqui.</p>
          <button class="btn btn--accent" id="cprRecarregar">Atualizar respostas</button>
        </div>`;
      body.querySelector("#cprRecarregar")!.addEventListener("click", () => {
        void etapaComparando(body);
      });
      return;
    }
    desenharMatriz(body, m);
  } catch (e) {
    body.innerHTML = `<p class="cpr-erro">${esc((e as Error).message)}</p>`;
  }
}

function desenharMatriz(body: HTMLElement, m: MatrizComparacao): void {
  const fornecedores = m.fornecedores;
  const central = m.centralizado;
  const vencedorCentral = central ? central.fornecedor_id : null;
  const pesos = carregarPesos();
  const recomendados =
    m.logica === "recomendado" ? calcularRecomendados(m.itens, fornecedores, pesos) : new Map<number, number>();

  body.innerHTML = `
    <div class="cpr-panel">
      <div class="cpr-matriz-head">
        <h3 class="cpr-titulo">Comparar propostas ${esc(m.cotacao.titulo ? "— “" + m.cotacao.titulo + "”" : "")}</h3>
        <div class="cpr-logica">
          <button class="btn${m.logica === "fracionado" ? " btn--accent" : ""}" data-logica="fracionado">💰 Melhor preço por item</button>
          <button class="btn${m.logica === "centralizado" ? " btn--accent" : ""}" data-logica="centralizado">📦 Melhor preço por lote</button>
          <button class="btn${m.logica === "recomendado" ? " btn--accent" : ""}" data-logica="recomendado">⭐ Recomendado</button>
        </div>
      </div>
      ${central ? `<p class="cpr-central">Opção de lote: <b>${esc(central.nome)}</b> — total ${fmtMoney(central.total)}</p>` : `<p class="cpr-central cpr-central-none">Nenhum fornecedor precificou todos os itens para a opção de lote.</p>`}
      ${m.logica === "recomendado" ? blocoPesos(pesos) : ""}
      <div class="cpr-ttrowe">
        <div class="cpr-tabwrap">
          <table class="cpr-matriz ${m.logica}">
            <thead><tr><th class="cpr-col-prod">Produto</th>
              ${fornecedores.map((f) => `<th>${esc(f.nome)}${f.status === "respondido" ? "" : '<span class="cpr-noresp">—</span>'}
                ${f.condicao_pagamento ? `<span class="cpr-cond-pgto" title="Condição de pagamento">${esc(f.condicao_pagamento)}</span>` : ""}</th>`).join("")}
            </tr></thead>
            <tbody>${m.itens.map((it) => linhaMatriz(it, fornecedores, m.logica, vencedorCentral, recomendados)).join("")}</tbody>
          </table>
        </div>
      </div>
      <p class="cpr-legenda">💰 melhor preço &nbsp;·&nbsp; 🚚 menor prazo de entrega ${m.logica === "recomendado" ? "&nbsp;·&nbsp; ⭐ recomendado (preço + prazo + pagamento)" : ""}</p>
      <div class="cpr-lista-foot" style="justify-content:space-between">
        <div style="display:flex;gap:8px;">
          <button class="btn" id="cprRecarregar2">↻ Atualizar respostas</button>
          <button class="btn" id="cprImportarIA">⚡ Importar resposta IA</button>
        </div>
        <button class="btn btn--accent" id="cprGerarPedidos">Gerar Pedidos ➔</button>
      </div>
    </div>`;
  body.querySelectorAll<HTMLElement>("[data-logica]").forEach((b) =>
    b.addEventListener("click", () => {
      m.logica = b.dataset.logica as string;
      desenharMatriz(body, m);
    })
  );
  body.querySelector("#cprRecarregar2")!.addEventListener("click", () => {
    void etapaComparando(body);
  });
  if (m.logica === "recomendado") {
    body.querySelectorAll<HTMLInputElement>("[data-peso]").forEach((slider) => {
      slider.addEventListener("input", () => {
        const atual = carregarPesos();
        const chave = slider.dataset.peso as keyof Pesos;
        atual[chave] = Number(slider.value);
        salvarPesos(atual);
        desenharMatriz(body, m);
      });
    });
  }
  body.querySelector("#cprImportarIA")!.addEventListener("click", () => {
    const opts = {
      cotacaoId: S.cotacaoId!,
      fornecedores,
      titulo: m.cotacao.titulo || ("Cotação " + m.cotacao.numero),
      onAplicado: () => desenhar(appScope(body)),
    };
    if (importarIa) {
      importarIa(opts);
    } else {
      void import("./importia")
        .then((mod) => mod.abrir(opts))
        .catch(() => toast("Importador IA indisponível.", "error"));
    }
  });
  body.querySelector<HTMLButtonElement>("#cprGerarPedidos")!.addEventListener("click", async () => {
    const btn = body.querySelector<HTMLButtonElement>("#cprGerarPedidos");
    if (btn) {
      btn.disabled = true;
      btn.classList.add("is-loading");
      btn.innerHTML = '<span class="spinner"></span> Gerando…';
    }
    try {
      // O backend só entende fracionado/centralizado; "recomendado" gera
      // pedidos usando a escolha calculada no cliente (fracionado como base
      // de agrupamento, já que cada item pode ir a um fornecedor diferente).
      const logicaEnvio = m.logica === "recomendado" ? "fracionado" : m.logica;
      await api.gerarPedidos(S.cotacaoId!, logicaEnvio);
      S.etapa = 4;
      desenhar(appScope(body));
    } catch (e) {
      if (btn) {
        btn.disabled = false;
        btn.classList.remove("is-loading");
        btn.innerHTML = "Gerar Pedidos ➔";
      }
      toast((e as Error).message, "error");
    }
  });
}

function blocoPesos(pesos: Pesos): string {
  return `
    <div class="cpr-pesos">
      <span class="cpr-pesos-rot">Priorizar:</span>
      <label class="cpr-peso"><span>💰 Preço</span>
        <input type="range" min="0" max="100" step="5" value="${pesos.preco}" data-peso="preco">
        <b>${pesos.preco}%</b>
      </label>
      <label class="cpr-peso"><span>🚚 Prazo</span>
        <input type="range" min="0" max="100" step="5" value="${pesos.prazo}" data-peso="prazo">
        <b>${pesos.prazo}%</b>
      </label>
      <label class="cpr-peso"><span>💳 Pagamento</span>
        <input type="range" min="0" max="100" step="5" value="${pesos.pagamento}" data-peso="pagamento">
        <b>${pesos.pagamento}%</b>
      </label>
    </div>`;
}

function linhaMatriz(
  item: MatrizItem,
  fornecedores: CotacaoFornecedor[],
  logica: string,
  vencedorCentral: number | null,
  recomendados: Map<number, number>
): string {
  const recomendadoId = recomendados.get(item.cotacao_item_id) ?? null;
  const cells = fornecedores
    .map((f) => {
      const pr = item.precos[String(f.fornecedor_id)];
      if (!pr) return `<td><span class="cpr-x">—</span></td>`;

      const ehVencedorPrincipal =
        logica === "centralizado"
          ? vencedorCentral === f.fornecedor_id && pr.disponivel && pr.preco_liquido > 0
          : logica === "recomendado"
            ? recomendadoId === f.fornecedor_id
            : item.melhor_id === f.fornecedor_id;

      const ehMelhorPreco = item.melhor_id === f.fornecedor_id;
      const ehMenorPrazo = item.melhor_prazo_id === f.fornecedor_id && item.melhor_prazo_id !== item.melhor_id;

      const badges =
        (logica === "recomendado" && ehVencedorPrincipal ? '<span class="cpr-mini-badge" title="Recomendado">⭐</span>' : "") +
        (logica !== "centralizado" && ehMelhorPreco ? '<span class="cpr-mini-badge" title="Melhor preço">💰</span>' : "") +
        (ehMenorPrazo ? '<span class="cpr-mini-badge" title="Menor prazo de entrega">🚚</span>' : "");

      const cls = ehVencedorPrincipal ? " cpr-melhor" : "";
      return `<td class="cpr-prece${cls}">${pr.disponivel ? "" : "<span class='cpr-esgot'>s/ estoque</span>"}
        <b>${fmtMoney(pr.preco_liquido)}</b> ${badges}
        <small>${pr.desconto ? "desconto " + pr.desconto + "%" : ""}${pr.prazo ? " · " + pr.prazo + "d" : ""}</small></td>`;
    })
    .join("");
  return `<tr><td class="cpr-col-prod"><b>${esc(item.name)}</b><small>qtd ${item.quantidade}</small></td>${cells}</tr>`;
}

// ============================================================ ETAPA 4

async function etapaPedidos(body: HTMLElement): Promise<void> {
  body.innerHTML = `<div class="cpr-panel">${barra("Gerando pedidos…")}</div>`;
  try {
    const pedidos = await api.listarPedidos();
    const meus = pedidos.filter((p) => p.cotacao_id === S.cotacaoId);
    body.innerHTML = `
      <div class="cpr-panel">
        <h3 class="cpr-titulo">Pedidos gerados — envie para os fornecedores</h3>
        <p class="cpr-sub">Cada pedido consolida os itens vencedores por fornecedor.</p>
        <div id="cprPedidos"></div>
      </div>`;
    const box = body.querySelector("#cprPedidos");
    if (!box) return;
    if (!meus.length) {
      box.innerHTML = `<p class="cpr-vazio">Nenhum pedido ainda.</p>`;
      return;
    }
    box.innerHTML = meus
      .map(
        (p) => `
      <div class="cpr-pedido">
        <div class="cpr-pedido-top">
          <div><b>Pedido ${esc(p.numero)}</b><span class="cpr-lk-status">${esc(p.fornecedor)}</span></div>
          <div class="cpr-pedido-total">${fmtMoney(p.total)}</div>
        </div>
        <div class="cpr-pedido-acao">
          <a class="btn" target="_blank" href="/compras/pedidos/${esc(p.id)}/imprimir">PDF</a>
          ${p.whatsapp ? `<a class="btn btn--wa" target="_blank" rel="noopener"
              href="https://wa.me/${esc(p.whatsapp)}?text=${encodeURIComponent("Olá " + p.fornecedor + ", segue nosso pedido de compras número " + p.numero + " referente à cotação aprovada. Aguardamos o faturamento e entrega!")}">WhatsApp</a>` : ""}
        </div>
      </div>`
      )
      .join("");
  } catch (e) {
    body.innerHTML = `<p class="cpr-erro">${esc((e as Error).message)}</p>`;
  }
}