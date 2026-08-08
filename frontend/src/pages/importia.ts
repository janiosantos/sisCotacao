// pages/importia.ts — modal de importação IA: cola texto (WhatsApp) ou envia PDF,
// cruza com o catálogo real (busca semântica) e aplica os preços na cotação aberta.
// Port de catalog_server/static/page_importia.js.

import {
  api,
  type IAExtrairResult,
  type IAMatchItem,
} from "../api/client";
import { escapeHtml, fmtMoney } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

export interface ImportIAFornecedor {
  id?: number | null;
  fornecedor_id?: number | null;
  nome: string;
}

export interface ImportIAOpts {
  cotacaoId: number;
  fornecedores?: ImportIAFornecedor[];
  titulo?: string;
  onAplicado?: () => void;
}

interface ItemSelecionado {
  produto_fornecedor?: string;
  preco_extraido?: number | null;
  candidatos?: IAMatchItem["candidatos"];
}

let state: {
  cotacaoId: number | null;
  fornecedores: ImportIAFornecedor[];
  fornecedorId: number | null;
  itens: ItemSelecionado[];
  onAplicado: (() => void) | null;
} = {
  cotacaoId: null,
  fornecedores: [],
  fornecedorId: null,
  itens: [],
  onAplicado: null,
};

function esc(s: unknown): string {
  return escapeHtml(s == null ? "" : s);
}

function money(v: number | null | undefined): string {
  return fmtMoney(v);
}

function spin(texto: string): string {
  return `<div class="ia-carregando"><span class="spinner"></span> ${esc(texto)}</div>`;
}

function fornecedorIdDe(fc: ImportIAFornecedor): number | null {
  const id = fc.id != null ? fc.id : fc.fornecedor_id != null ? fc.fornecedor_id : null;
  return id != null ? Number(id) : null;
}

export function render($app: HTMLElement): void {
  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Importação IA</h1>
        <p class="page-sub">Assistente de leitura de retornos de fornecedores (WhatsApp/PDF) — aberto a partir da tela de cotação.</p>
      </div>
    </div>
    <div class="empty-box"><p>Nada por aqui</p><p>Abra uma cotação e use o botão "Importar retorno" para colar a resposta do fornecedor.</p></div>`;
}

export function abrir(opts: ImportIAOpts): void {
  state.cotacaoId = opts.cotacaoId;
  state.fornecedores = opts.fornecedores || [];
  state.onAplicado = opts.onAplicado || null;
  const f0 = state.fornecedores[0] || {};
  state.fornecedorId = fornecedorIdDe(f0);

  const foptions =
    state.fornecedores.length > 1
      ? `<div class="field"><label>Fornecedor</label>
           <select id="iaFornecedor">
             ${state.fornecedores
               .map((fc) => {
                 const id = fornecedorIdDe(fc);
                 return `<option value="${id}" ${id === state.fornecedorId ? "selected" : ""}>${esc(fc.nome)}</option>`;
               })
               .join("")}
           </select>
         </div>`
      : `<div class="field"><label>Fornecedor</label>
           <div style="padding:6px 0;font-size:13px;"><strong>${esc(f0.nome || "—")}</strong></div>
         </div>`;

  openModal(
    `<div class="modal-head">
       <div>
         <h3>Importar resposta${opts.titulo ? " — " + esc(opts.titulo) : ""}</h3>
         <p style="font-size:12px;color:var(--ink-soft);margin-top:2px;">
           Cole o retorno do fornecedor (WhatsApp/e-mail) ou anexe o PDF do orçamento. A IA extrai os itens
           e cruza com o catálogo real — revise antes de aplicar.
         </p>
       </div>
       <button class="icon-btn" data-close>×</button>
     </div>
     <div style="display:flex;flex-direction:column;gap:14px;">
       ${foptions}
       <div class="ia-tabs">
         <button class="ia-tab is-cur" data-ia-tab="texto">Texto / WhatsApp</button>
         <button class="ia-tab" data-ia-tab="pdf">PDF</button>
       </div>
       <div id="iaPainelTexto">
         <div class="field"><label>Mensagem / retorno do fornecedor</label>
           <textarea id="iaTexto" rows="5" placeholder="Ex.: Parafuso 10x100 — R$ 0,45 /un&#10;Chave de fenda 6x150 — R$ 12,90"></textarea>
         </div>
         <button class="btn btn--accent" id="btnExtrair">Extrair itens ➔</button>
       </div>
       <div id="iaPainelPdf" hidden>
         <div class="field"><label>Arquivo PDF do orçamento</label>
           <input type="file" id="iaArquivo" accept=".pdf">
         </div>
         <button class="btn btn--accent" id="btnExtrairPdf">Extrair do PDF ➔</button>
       </div>
       <div id="iaResultado"></div>
     </div>
     <div class="modal-actions" style="align-items:center;">
       <button class="btn btn--ghost btn--sm" id="iaSeed">↻ Recarregar catálogo</button>
       <span style="flex:1;"></span>
       <button class="btn" data-close>Fechar</button>
       <button class="btn btn--accent" id="iaAplicar" disabled>Aplicar preços na cotação</button>
     </div>`,
    { modalClass: "modal--ia", onMount }
  );
}

function onMount(modal: HTMLElement): void {
  modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));

  modal.querySelectorAll(".ia-tab").forEach((tab) =>
    tab.addEventListener("click", () => {
      modal.querySelectorAll(".ia-tab").forEach((t) => t.classList.remove("is-cur"));
      tab.classList.add("is-cur");
      const tabKey = (tab as HTMLElement).dataset.iaTab;
      (modal.querySelector("#iaPainelTexto") as HTMLElement).hidden = tabKey !== "texto";
      (modal.querySelector("#iaPainelPdf") as HTMLElement).hidden = tabKey !== "pdf";
    })
  );

  const selForn = modal.querySelector<HTMLSelectElement>("#iaFornecedor");
  if (selForn) selForn.addEventListener("change", () => { state.fornecedorId = Number(selForn.value); });

  modal.querySelector<HTMLButtonElement>("#btnExtrair")!.addEventListener("click", () => extrair(modal, null));
  modal.querySelector<HTMLButtonElement>("#btnExtrairPdf")!.addEventListener("click", () => {
    const file = (modal.querySelector<HTMLInputElement>("#iaArquivo")!.files || [])[0];
    if (!file) { toast("Selecione um arquivo PDF.", "error"); return; }
    extrair(modal, file);
  });

  modal.querySelector<HTMLButtonElement>("#iaSeed")!.addEventListener("click", () => sincronizarCatalogo(modal));
  modal.querySelector<HTMLButtonElement>("#iaAplicar")!.addEventListener("click", () => aplicar(modal));
}

async function extrair(modal: HTMLElement, file: File | null): Promise<void> {
  const btn = modal.querySelector<HTMLButtonElement>(file ? "#btnExtrairPdf" : "#btnExtrair")!;
  const resultBox = modal.querySelector<HTMLElement>("#iaResultado")!;
  btn.disabled = true;
  resultBox.innerHTML = file ? spin("Extraindo texto do PDF e identificando itens…") : spin("Identificando itens no retorno…");
  try {
    const res: IAExtrairResult = file
      ? await api.iaExtrairPdf(file)
      : await api.iaExtrairTexto((modal.querySelector<HTMLTextAreaElement>("#iaTexto")!.value || ""));
    const itens = (res.items || []).map((i) => ({
      produto_fornecedor: i.produto_fornecedor,
      preco_extraido: i.preco_extraido,
    }));
    if (!itens.length) {
      resultBox.innerHTML = `<p class="ia-info">Não identifiquei itens com preço nesse retorno. Confira o texto/PDF enviado.</p>`;
      return;
    }
    const match = await api.iaMatch(itens, 5);
    state.itens = (match.items || []).map((m) => ({
      produto_fornecedor: m.produto_fornecedor,
      preco_extraido: m.preco_extraido,
      candidatos: m.candidatos || [],
    }));
    renderResultado(modal);
  } catch (e) {
    resultBox.innerHTML = `<p class="ia-erro">${esc((e as Error).message)}</p>`;
  } finally {
    btn.disabled = false;
  }
}

function renderResultado(modal: HTMLElement): void {
  const box = modal.querySelector<HTMLElement>("#iaResultado")!;
  const rows = state.itens;
  box.innerHTML = `
    <div class="ia-info">${rows.length} item(ns) identificados — confira a correspondência com o catálogo. O melhor score de cada um é pré-selecionado.</div>
    <table class="data-table ia-table">
      <thead><tr>
        <th>Item do fornecedor</th><th>Preço</th>
        <th style="min-width:220px;">Produto do catálogo (semântico)</th><th>Confiança</th>
      </tr></thead>
      <tbody>
        ${rows.map((r, i) => linha(r, i)).join("")}
      </tbody>
    </table>
    <p style="font-size:11.5px;color:var(--ink-faint);margin:8px 0 0;">
      Itens em "Sem correspondência" não serão aplicados. Produtos que não estão nesta cotação são ignorados no lançamento.
    </p>`;
  modal.querySelectorAll<HTMLSelectElement>(".ia-cand").forEach((sel) =>
    sel.addEventListener("change", () => {
      const conf = box.querySelector<HTMLElement>(`[data-conf="${sel.dataset.row}"]`);
      const opt = sel.selectedOptions[0];
      if (conf) conf.textContent = opt.value ? Math.round(Number(opt.dataset.score) * 100) + "%" : "—";
    })
  );
  (modal.querySelector<HTMLButtonElement>("#iaAplicar")!).disabled = false;
}

function linha(r: ItemSelecionado, i: number): string {
  const opts = (r.candidatos || []).map((c, j) => {
    const rotulo = j === 0 ? " — melhor" : "";
    return `<option value="${c.produto_catalogo_id ?? ""}" data-score="${c.score}">${esc(c.produto_catalogo_nome)} (${Math.round(c.score * 100)}%)${rotulo}</option>`;
  }).join("");
  const primeiro = (r.candidatos || [])[0];
  return `
    <tr>
      <td><strong>${esc(r.produto_fornecedor)}</strong></td>
      <td class="ia-preco">${money(r.preco_extraido ?? null)}</td>
      <td>
        <select class="ia-cand" data-row="${i}" style="width:100%;">
          <option value="">Sem correspondência (não aplicar)</option>
          ${opts}
        </select>
      </td>
      <td class="ia-conf" data-conf="${i}">${primeiro ? Math.round(primeiro.score * 100) + "%" : "—"}</td>
    </tr>`;
}

async function aplicar(modal: HTMLElement): Promise<void> {
  const selections: { produto_id: number; preco_extraido: number | null; produto_fornecedor?: string }[] = [];
  const naoAssociados: string[] = [];
  state.itens.forEach((r, i) => {
    const sel = modal.querySelector<HTMLSelectElement>(`.ia-cand[data-row="${i}"]`);
    const val = sel && sel.value;
    if (!val) { if (r.produto_fornecedor) naoAssociados.push(r.produto_fornecedor); return; }
    selections.push({
      produto_id: Number(val),
      preco_extraido: r.preco_extraido ?? null,
      produto_fornecedor: r.produto_fornecedor,
    });
  });
  if (!selections.length) { toast("Nada para aplicar: nenhum item foi associado ao catálogo.", "error"); return; }

  const btn = modal.querySelector<HTMLButtonElement>("#iaAplicar")!;
  btn.disabled = true; btn.classList.add("is-loading");
  btn.innerHTML = '<span class="spinner"></span> Aplicando…';
  try {
    const res = await api.iaAplicar(state.cotacaoId ?? 0, {
      fornecedor_id: state.fornecedorId,
      selections,
    });
    closeModal();
    const nao = naoAssociados.length ? ` · ${naoAssociados.length} sem correspondência` : "";
    toast(`IA aplicada: ${res.aplicados} preço(s) lançado(s), ${(res.ignorados || []).length} ignorado(s).${nao}`, "success");
    if (state.onAplicado) state.onAplicado();
  } catch (e) {
    btn.disabled = false; btn.classList.remove("is-loading");
    btn.innerHTML = "Aplicar preços na cotação";
    toast("Erro ao aplicar: " + (e as Error).message, "error");
  }
}

async function sincronizarCatalogo(modal: HTMLElement): Promise<void> {
  const btn = modal.querySelector<HTMLButtonElement>("#iaSeed")!;
  btn.disabled = true; btn.classList.add("is-loading");
  btn.innerHTML = '<span class="spinner"></span> Reindexando…';
  try {
    const r = await api.iaSeed(false);
    toast(`Catálogo reindexado: ${r.populados} produtos (total ${r.total_catalogo}${r.troncado ? ", cap " + r.cap : ""}).`, "success");
  } catch (e) {
    toast("Falha ao reindexar: " + (e as Error).message, "error");
  } finally {
    btn.disabled = false; btn.classList.remove("is-loading");
    btn.innerHTML = "↻ Recarregar catálogo";
  }
}
