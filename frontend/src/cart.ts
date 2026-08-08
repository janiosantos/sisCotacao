// cart.ts — carrinho de cotações (cesta + painel lateral + exportação).
// Fonte única do rascunho de cotação (`cotacao_draft_v1`).

import { api, type DetalheCartItem } from "./api/client";
import { escapeHtml, fmtMoney } from "./ui/format";
import { closeModal, confirmDialog, openModal, toast } from "./ui/dom";

const DRAFT_KEY = "cotacao_draft_v1";

export interface CartDraft {
  itens: Record<number, number>;
  detalhes: Record<number, DetalheCartItem>;
}

export interface CartItemRow {
  id: number;
  qty: number;
  detail: DetalheCartItem;
}

// ---------------- estado ----------------

export function load(): CartDraft {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : { itens: {}, detalhes: {} };
  } catch {
    return { itens: {}, detalhes: {} };
  }
}

function save(d: CartDraft): void {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(d));
}

function emit(): void {
  document.dispatchEvent(new CustomEvent("cart:updated"));
}

function itens(): Record<number, number> {
  return load().itens || {};
}

function detalhes(): Record<number, DetalheCartItem> {
  return load().detalhes || {};
}

// ---------------- mutações ----------------

export function addItem(variantId: number, qty: number, det: Partial<DetalheCartItem>): void {
  const d = load();
  d.itens = d.itens || {};
  d.detalhes = d.detalhes || {};
  d.itens[variantId] = (Number(d.itens[variantId]) || 0) + (Number(qty) || 0);
  if (det) d.detalhes[variantId] = { id: variantId, name: det.name || "", price: det.price || 0, ...det };
  save(d);
  emit();
}

export function setQty(variantId: number, qty: number, det: Partial<DetalheCartItem>): void {
  const d = load();
  d.itens = d.itens || {};
  d.detalhes = d.detalhes || {};
  if (Number(qty) <= 0) {
    delete d.itens[variantId];
    delete d.detalhes[variantId];
  } else {
    d.itens[variantId] = Number(qty);
    if (det) d.detalhes[variantId] = { id: variantId, name: det.name || "", price: det.price || 0, ...det };
  }
  save(d);
  emit();
}

export function remove(variantId: number): void {
  const d = load();
  delete d.itens[variantId];
  delete d.detalhes[variantId];
  save(d);
  emit();
}

export function clear(): void {
  save({ itens: {}, detalhes: {} });
  emit();
}

// ---------------- leituras ----------------

export function countItens(): number {
  return Object.values(itens()).filter((n) => Number(n) > 0).length;
}

export function totalQtd(): number {
  return Object.values(itens()).reduce((s, n) => s + (Number(n) || 0), 0);
}

export function totalValor(): number {
  const det = detalhes();
  return Object.entries(itens()).reduce((s, [id, q]) => {
    const d = det[Number(id)];
    return s + (d && d.price ? Number(d.price) : 0) * (Number(q) || 0);
  }, 0);
}

export function list(): CartItemRow[] {
  const det = detalhes();
  return Object.entries(itens())
    .filter(([, q]) => Number(q) > 0)
    .map(([id, q]) => ({ id: Number(id), qty: Number(q), detail: det[Number(id)] || ({} as DetalheCartItem) }))
    .sort((a, b) => (a.detail.name || "").localeCompare(b.detail.name || "", "pt"));
}

// ---------------- UI: painel lateral + sidebar ----------------

let sbScope: HTMLElement | null = null;

function rowHtml({ id, qty, detail }: CartItemRow): string {
  return `
    <div class="cart-item">
      <div class="cart-item-img">${detail.imagem_url ? `<img class="cart-item-thumb" src="${escapeHtml(detail.imagem_url)}" alt="">` : `<span class="cart-item-ph">·</span>`}</div>
      <div class="cart-item-body">
        <p class="cart-item-name">${escapeHtml(detail.name || "Produto #" + id)}</p>
        ${detail.spec ? `<p class="cart-item-spec">${escapeHtml(detail.spec)}</p>` : ""}
        ${detail.brand ? `<p class="cart-item-brand">${escapeHtml(detail.brand)}</p>` : ""}
        <div class="cart-item-ctrls">
          <button class="cart-stepper" data-minus="${id}" type="button">–</button>
          <input class="cart-qty" type="number" min="0" step="1" value="${qty}" data-id="${id}">
          <button class="cart-stepper" data-plus="${id}" type="button">+</button>
          <span class="cart-item-price">${detail.price ? fmtMoney(detail.price) : "—"}</span>
        </div>
      </div>
      <button class="cart-item-rm" data-rm="${id}" type="button" title="Remover">×</button>
    </div>`;
}

function bindList($list: HTMLElement): void {
  $list.querySelectorAll<HTMLElement>("[data-minus]").forEach((b) => {
    b.onclick = () => setQty(Number(b.dataset.minus), (itens()[Number(b.dataset.minus)] || 0) - 1, {});
  });
  $list.querySelectorAll<HTMLElement>("[data-plus]").forEach((b) => {
    b.onclick = () => setQty(Number(b.dataset.plus), (itens()[Number(b.dataset.plus)] || 0) + 1, {});
  });
  $list.querySelectorAll<HTMLInputElement>(".cart-qty").forEach((i) => {
    i.onchange = () => setQty(Number(i.dataset.id), Math.max(0, parseInt(i.value, 10) || 0), {});
  });
  $list.querySelectorAll<HTMLElement>("[data-rm]").forEach((b) => {
    b.onclick = () => remove(Number(b.dataset.rm));
  });
}

function renderPanel(): void {
  const items = list();
  const $list = document.getElementById("cartList");
  const $total = document.getElementById("cartTotal");
  const $vazio = document.getElementById("cartVazio");
  if (!$list) return;
  if (!items.length) {
    $list.innerHTML = "";
    if ($vazio) $vazio.style.display = "";
    if ($total) $total.textContent = fmtMoney(0);
    return;
  }
  if ($vazio) $vazio.style.display = "none";
  $list.innerHTML = items.map(rowHtml).join("");
  if ($total) $total.textContent = fmtMoney(totalValor());
  bindList($list);
}

function refillS(): void {
  if (!sbScope) return;
  const $list = sbScope.querySelector<HTMLElement>(".cart-list");
  const $vazio = sbScope.querySelector<HTMLElement>(".cart-vazio");
  const $total = sbScope.querySelector<HTMLElement>(".cart-total-strong");
  const $info = sbScope.querySelector<HTMLElement>(".cart-sidebar-count");
  if (!$list) return;
  const items = list();
  if (!items.length) {
    $list.innerHTML = "";
    if ($vazio) $vazio.style.display = "";
    if ($total) $total.textContent = fmtMoney(0);
  } else {
    if ($vazio) $vazio.style.display = "none";
    $list.innerHTML = items.map(rowHtml).join("");
    if ($total) $total.textContent = fmtMoney(totalValor());
  }
  if ($info) $info.textContent = `${countItens()} item(ns) · ${totalQtd()} unidade(s)`;
  bindList($list);
}

let opened = false;

export function toggle(force?: boolean): void {
  const $overlay = document.getElementById("cartOverlay");
  if (!$overlay) return;
  opened = force != null ? force : !opened;
  $overlay.classList.toggle("is-open", opened);
  document.body.style.overflow = opened ? "hidden" : "";
  if (opened) renderPanel();
}

function syncBtn(): void {
  const $btn = document.getElementById("cartBtn");
  if (!$btn) return;
  $btn.style.display = document.querySelector(".cart-sidebar") ? "none" : "";
}

// ---------------- sidebar fixa (catálogo 70/30) ----------------

export function mountSidebar(container: HTMLElement): void {
  if (!container || container.querySelector(".cart-sidebar")) return;
  container.innerHTML = `
    <aside class="cart-sidebar">
      <div class="cart-sidebar-head">
        <h3>Carrinho</h3>
        <div class="cart-head-actions">
          <button class="btn btn--ghost btn--sm" id="sbLimpar" type="button">Esvaziar</button>
          <span class="cart-sidebar-count" id="sbInfo"></span>
        </div>
      </div>
      <div class="cart-sidebar-body">
        <div class="cart-list" id="sbList"></div>
        <div class="cart-vazio" id="sbVazio">Seu carrinho está vazio.<br>Escolha quantidades no catálogo.</div>
      </div>
      <div class="cart-foot">
        <div class="cart-total"><span>Total estimado</span><strong class="cart-total-strong" id="sbTotal">—</strong></div>
        <p class="cart-foot-hint">Envio rápido — você mesmo compara as respostas</p>
        <button class="btn btn--accent cart-cta" id="sbWhats" type="button">
          <span class="cart-cta-ico">💬</span> Enviar pedido via WhatsApp
        </button>
        <button class="btn cart-cta cart-cta--pdf" id="sbPdf" type="button">
          <span class="cart-cta-ico">📄</span> Gerar PDF para e-mail
        </button>
        <p class="cart-foot-hint">Ou deixe o sistema comparar os preços por você</p>
        <button class="btn btn--outline cart-cta" id="sbCriar" type="button">Criar cotação →</button>
      </div>
    </aside>`;
  const sb = container.querySelector<HTMLElement>(".cart-sidebar");
  sbScope = sb;
  if (!sb) return;
  sb.querySelector<HTMLElement>("#sbLimpar")!.onclick = async () => {
    if (!(await confirmDialog("Limpar todos os itens do carrinho?"))) return;
    clear();
  };
  sb.querySelector<HTMLElement>("#sbWhats")!.onclick = () => void enviarWhatsapp();
  sb.querySelector<HTMLElement>("#sbPdf")!.onclick = () => gerarPdf();
  sb.querySelector<HTMLElement>("#sbCriar")!.onclick = () => void criarCotacao(sb.querySelector<HTMLElement>("#sbCriar") as HTMLButtonElement);
  refillS();
  syncBtn();
}

// ---------------- exportação ----------------

function mensagemWhatsapp(): string {
  const items = list();
  if (!items.length) return "";
  const linhas = ["*PEDIDO DE COTAÇÃO*", "Itens selecionados:"];
  items.forEach(({ qty, detail }, i) => {
    const specs = [];
    if (detail.spec) specs.push(detail.spec);
    if (detail.brand) specs.push(detail.brand);
    const extra = specs.length ? ` (${specs.join(" · ")})` : "";
    const preco = detail.price ? ` — ${fmtMoney(detail.price)}` : "";
    linhas.push(`${i + 1}. ${detail.name || "Produto"}${extra} — qtd: ${qty}${preco}`);
  });
  const total = items.reduce((s, { qty, detail }) => s + (detail.price || 0) * qty, 0);
  linhas.push(`*Total estimado: ${fmtMoney(total)}*`);
  linhas.push("");
  linhas.push("Aguardando melhor preço.");
  return linhas.join("\n");
}

function apenasDigitos(s: string | null): string {
  return String(s || "").replace(/\D/g, "");
}

async function enviarWhatsapp(): Promise<void> {
  const msg = mensagemWhatsapp();
  if (!msg) {
    toast("Seu carrinho está vazio", "error");
    return;
  }
  let comNumero: Array<{ id: number; nome: string; whatsapp: string | null }> = [];
  try {
    comNumero = (await api.listarFornecedores(true)).filter((f) => apenasDigitos(f.whatsapp));
  } catch {
    /* segue com lista vazia */
  }

  if (!comNumero.length) {
    window.open("https://wa.me/?text=" + encodeURIComponent(msg), "_blank", "noopener");
    return;
  }

  openModal(
    `<div class="modal-head"><h3>Enviar para qual fornecedor?</h3><button class="icon-btn" data-close>×</button></div>
     <div class="wa-forn-list">
       ${comNumero.map((f) => `<button type="button" class="btn wa-forn-btn" data-forn="${f.id}">${escapeHtml(f.nome)}</button>`).join("")}
       <button type="button" class="btn btn--ghost wa-forn-btn" data-outro>Outro contato (escolher no WhatsApp)</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll<HTMLElement>("[data-close]").forEach((b) => (b.onclick = closeModal));
        modal.querySelector<HTMLElement>("[data-outro]")!.onclick = () => {
          closeModal();
          window.open("https://wa.me/?text=" + encodeURIComponent(msg), "_blank", "noopener");
        };
        modal.querySelectorAll<HTMLElement>("[data-forn]").forEach((b) => {
          b.onclick = () => {
            const f = comNumero.find((x) => String(x.id) === b.dataset.forn);
            closeModal();
            if (!f) return;
            window.open(`https://wa.me/${apenasDigitos(f.whatsapp)}?text=` + encodeURIComponent(msg), "_blank", "noopener");
          };
        });
      },
    }
  );
}

function gerarPdf(): void {
  const items = list();
  if (!items.length) {
    toast("Seu carrinho está vazio", "error");
    return;
  }
  const w = window.open("", "_blank", "noopener");
  if (!w) {
    toast("Bloqueio de pop-up: permita abrir novas janelas", "error");
    return;
  }
  const hoje = new Date().toLocaleDateString("pt-BR");
  const rows = items
    .map(
      ({ qty, detail }, i) => `
      <tr>
        <td class="num">${i + 1}</td>
        <td>
          <div class="item-nome">${escapeHtml(detail.name || "Produto #" + (detail.id || ""))}</div>
          ${detail.spec ? `<div class="item-spec">${escapeHtml(detail.spec)}</div>` : ""}
          ${detail.brand ? `<div class="item-brand">${escapeHtml(detail.brand)}</div>` : ""}
        </td>
        <td class="qtd">${qty}</td>
        <td class="preco">${detail.price ? fmtMoney(detail.price) : "—"}</td>
        <td class="preco">${detail.price ? fmtMoney(detail.price * qty) : "—"}</td>
      </tr>`
    )
    .join("");
  const total = items.reduce((s, { qty, detail }) => s + (detail.price || 0) * qty, 0);
  w.document.write(`<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Pedido de cotação — ${hoje}</title>
<style>
  *{box-sizing:border-box}
  body{font-family:'Segoe UI',Arial,sans-serif;color:#1d2733;margin:32px}
  h1{font-size:18px;margin:0 0 4px}
  .sub{color:#5b6b7c;font-size:12px;margin-bottom:20px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{background:#1F3A5F;color:#fff;text-align:left;padding:7px 10px;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
  td{padding:8px 10px;border-bottom:1px solid #e2e8ef;vertical-align:top}
  .num{width:32px;color:#5b6b7c}
  .qtd{width:70px;text-align:center}
  .preco{width:120px;text-align:right;white-space:nowrap}
  .item-nome{font-weight:600}
  .item-spec,.item-brand{color:#5b6b7c;font-size:12px}
  .total-row td{border-top:2px solid #1F3A5F;font-weight:700;font-size:14px}
  .rodape{margin-top:28px;font-size:11px;color:#5b6b7c}
</style>
</head>
<body>
  <h1>Pedido de Cotação</h1>
  <div class="sub">Gerado em ${hoje} · ${items.length} item(ns) · Sistema de Cotações</div>
  <table>
    <thead><tr><th>#</th><th>Item</th><th>Qtd</th><th>Preço unit.</th><th>Subtotal</th></tr></thead>
    <tbody>${rows}</tbody>
    <tfoot><tr class="total-row"><td colspan="4">Total estimado</td><td class="preco">${fmtMoney(total)}</td></tr></tfoot>
  </table>
  <div class="rodape">Valores estimados para comparação entre distribuidores. Sujeito à confirmação de preço e disponibilidade.</div>
  <script>window.onload = function(){ window.print(); };<\/script>
</body>
</html>`);
  w.document.close();
}

function setLoading(btn: HTMLElement | null, on: boolean): void {
  if (!btn) return;
  (btn as HTMLButtonElement).disabled = on;
  btn.classList.toggle("is-loading", on);
  if (on) {
    btn.dataset.label = btn.textContent?.trim() ?? "";
    btn.innerHTML = `<span class="spinner" aria-hidden="true"></span> Processando...`;
  } else {
    btn.innerHTML = btn.dataset.label || btn.innerHTML;
    delete btn.dataset.label;
  }
}

// ---------------- criar cotação (RFQ) ----------------

export async function criarCotacao(btn: HTMLElement | null): Promise<void> {
  const lista = list();
  if (!lista.length) {
    toast("Adicione pelo menos um item para criar a cotação", "error");
    return;
  }
  const payloadItens = lista.map(({ id, qty, detail }) => ({
    produto_id: id,
    variante_id: id,
    quantidade: qty,
    preco_estimado: detail.price != null ? Number(detail.price) : null,
  }));

  setLoading(btn, true);
  try {
    let fornecedores: Array<{ id: number; nome: string }> = [];
    try {
      fornecedores = await api.listarFornecedores(true);
    } catch {
      /* segue sem fornecedores */
    }
    const fornecedoresHtml = fornecedores.length
      ? fornecedores
          .map(
            (f) => `
            <label style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:13.5px;">
              <input type="checkbox" name="fornecedor" value="${f.id}">
              ${escapeHtml(f.nome)}
            </label>`
          )
          .join("")
      : `<p style="font-size:13px;color:var(--ink-soft);">Nenhum fornecedor cadastrado ainda. Você pode criar a cotação mesmo assim e convidar fornecedores depois.</p>`;

    openModal(
      `<div class="modal-head"><h3>Nova cotação</h3><button class="icon-btn" data-close>×</button></div>
       <div style="display:flex;flex-direction:column;gap:14px;">
         <div class="field"><label>Título (opcional)</label><input id="mTitulo" type="text" placeholder="Ex.: Reposição mensal"></div>
         <div class="field"><label>Cliente (opcional)</label><input id="mCliente" type="text" placeholder="Nome do cliente atendido"></div>
         <div class="field"><label>Observações (opcional)</label><textarea id="mObs" placeholder="Prazo desejado, condições, etc."></textarea></div>
         <div class="field"><label>Enviar para quais fornecedores?</label>
           <div style="max-height:180px;overflow-y:auto;border:1px solid var(--line);border-radius:3px;padding:4px 10px;">
             ${fornecedoresHtml}
           </div>
         </div>
       </div>
       <div class="modal-actions">
         <button class="btn" data-close>Cancelar</button>
         <button class="btn btn--accent" id="btnConfirmarCriar">Criar cotação</button>
       </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll<HTMLElement>("[data-close]").forEach((b) => (b.onclick = closeModal));
          modal.querySelector<HTMLButtonElement>("#btnConfirmarCriar")!.onclick = async () => {
            const fornecedor_ids = [...modal.querySelectorAll<HTMLInputElement>('input[name="fornecedor"]:checked')].map(
              (el) => Number(el.value)
            );
            if (!payloadItens.length) {
              toast("Adicione pelo menos um item para criar a cotação", "error");
              return;
            }
            const $confirm = modal.querySelector<HTMLElement>("#btnConfirmarCriar");
            setLoading($confirm, true);
            try {
              const res = await api.criarCotacao({
                titulo: modal.querySelector<HTMLInputElement>("#mTitulo")!.value.trim() || null,
                cliente: modal.querySelector<HTMLInputElement>("#mCliente")!.value.trim() || null,
                observacoes: modal.querySelector<HTMLTextAreaElement>("#mObs")!.value.trim() || null,
                fornecedor_ids,
                itens: payloadItens.map(({ produto_id, quantidade }) => ({ produto_id, quantidade })),
              });
              clear();
              closeModal();
              toast(`Cotação nº ${res.numero} criada`, "success");
              location.hash = `#/cotacoes/${res.id}`;
            } catch (e) {
              toast("Erro ao criar cotação: " + (e as Error).message, "error");
            } finally {
              setLoading($confirm, false);
            }
          };
        },
      }
    );
    if (opened) toggle(false);
  } finally {
    setLoading(btn, false);
  }
}

// ---------------- init / overlay ----------------

export function injectOverlay(): void {
  const $topbar = document.querySelector(".topbar");
  if ($topbar && !document.getElementById("cartBtn")) {
    const $btn = document.createElement("button");
    $btn.id = "cartBtn";
    $btn.type = "button";
    $btn.className = "cart-btn";
    $btn.title = "Carrinho de cotações";
    $btn.innerHTML = `<span class="cart-ico" aria-hidden="true">🛒</span><span id="cartCount" class="cart-count">0</span>`;
    $topbar.appendChild($btn);
    $btn.onclick = () => toggle();
  }

  if (!document.getElementById("cartOverlay")) {
    const $panel = document.createElement("div");
    $panel.id = "cartOverlay";
    $panel.className = "cart-overlay";
    $panel.innerHTML = `
      <aside class="cart-panel">
        <div class="cart-head">
          <h3>Carrinho</h3>
          <div class="cart-head-actions">
            <button class="btn btn--ghost btn--sm" id="cartLimpar" type="button">Esvaziar</button>
            <button class="icon-btn" id="cartClose" type="button">×</button>
          </div>
        </div>
        <div class="cart-count-info" id="cartInfo"></div>
        <div class="cart-list" id="cartList"></div>
        <div class="cart-vazio" id="cartVazio">Seu carrinho está vazio.<br>Escolha quantidades no catálogo.</div>
        <div class="cart-foot">
          <div class="cart-total"><span>Total estimado</span><strong id="cartTotal">—</strong></div>
          <p class="cart-foot-hint">Envio rápido — você mesmo compara as respostas</p>
          <button class="btn btn--accent cart-cta" id="cartWhats" type="button">
            <span class="cart-cta-ico">💬</span> Enviar pedido via WhatsApp
          </button>
          <button class="btn cart-cta cart-cta--pdf" id="cartPdf" type="button">
            <span class="cart-cta-ico">📄</span> Gerar PDF para e-mail
          </button>
          <p class="cart-foot-hint">Ou deixe o sistema comparar os preços por você</p>
          <button class="btn btn--outline cart-cta" id="cartCriar" type="button">Criar cotação e convidar fornecedores →</button>
        </div>
      </aside>`;
    document.body.appendChild($panel);

    $panel.querySelector<HTMLElement>("#cartClose")!.onclick = () => toggle(false);
    $panel.addEventListener("click", (e) => {
      if (e.target === $panel) toggle(false);
    });
    $panel.querySelector<HTMLElement>("#cartWhats")!.onclick = () => void enviarWhatsapp();
    $panel.querySelector<HTMLElement>("#cartPdf")!.onclick = () => gerarPdf();
    $panel.querySelector<HTMLElement>("#cartCriar")!.onclick = () => criarCotacao($panel.querySelector<HTMLElement>("#cartCriar"));
    $panel.querySelector<HTMLElement>("#cartLimpar")!.onclick = async () => {
      if (!(await confirmDialog("Limpar todos os itens do carrinho?"))) return;
      clear();
    };
  }

  const $info = document.getElementById("cartInfo");
  const updateInfo = () => {
    if ($info) $info.textContent = `${countItens()} item(ns) · ${totalQtd()} unidade(s)`;
  };
  document.addEventListener("cart:updated", badge);
  document.addEventListener("cart:updated", renderPanel);
  document.addEventListener("cart:updated", updateInfo);
  document.addEventListener("cart:updated", refillS);
  window.addEventListener("hashchange", syncBtn);
  badge();
  updateInfo();
  syncBtn();
}

function badge(): void {
  const n = countItens();
  const $b = document.getElementById("cartBtn");
  const $c = document.getElementById("cartCount");
  if ($b) $b.classList.toggle("has-items", n > 0);
  if ($c) $c.textContent = String(n);
}