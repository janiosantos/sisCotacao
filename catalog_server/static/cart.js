// cart.js — carrinho de cotações (cesta no header + painel lateral + exportação).
// Fonte única de verdade do rascunho de cotação (`cotacao_draft_v1`).
const Cart = (() => {
  const DRAFT_KEY = "cotacao_draft_v1";

  // ---------------- estado ----------------

  function load() {
    try {
      const raw = localStorage.getItem(DRAFT_KEY);
      return raw ? JSON.parse(raw) : { itens: {}, detalhes: {} };
    } catch (e) {
      return { itens: {}, detalhes: {} };
    }
  }

  function save(d) {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(d));
  }

  function emit() {
    document.dispatchEvent(new CustomEvent("cart:updated"));
  }

  function itens() {
    return load().itens || {};
  }

  function detalhes() {
    return load().detalhes || {};
  }

  // ---------------- mutações ----------------

  function addItem(variantId, qty, det) {
    const d = load();
    d.itens = d.itens || {};
    d.detalhes = d.detalhes || {};
    d.itens[variantId] = (Number(d.itens[variantId]) || 0) + (Number(qty) || 0);
    if (det) d.detalhes[variantId] = det;
    save(d);
    emit();
  }

  function setQty(variantId, qty, det) {
    const d = load();
    d.itens = d.itens || {};
    d.detalhes = d.detalhes || {};
    if (Number(qty) <= 0) {
      delete d.itens[variantId];
      delete d.detalhes[variantId];
    } else {
      d.itens[variantId] = Number(qty);
      if (det) d.detalhes[variantId] = det;
    }
    save(d);
    emit();
  }

  function remove(variantId) {
    const d = load();
    delete d.itens[variantId];
    delete d.detalhes[variantId];
    save(d);
    emit();
  }

  function clear() {
    save({ itens: {}, detalhes: {} });
    emit();
  }

  // ---------------- leituras ----------------

  function countItens() {
    return Object.values(itens()).filter((n) => Number(n) > 0).length;
  }

  function totalQtd() {
    return Object.values(itens()).reduce((s, n) => s + (Number(n) || 0), 0);
  }

  function totalValor() {
    const det = detalhes();
    return Object.entries(itens()).reduce((s, [id, q]) => {
      const d = det[id];
      return s + (d && d.price ? Number(d.price) : 0) * (Number(q) || 0);
    }, 0);
  }

  function list() {
    const det = detalhes();
    return Object.entries(itens())
      .filter(([, q]) => Number(q) > 0)
      .map(([id, q]) => ({ id: Number(id), qty: Number(q), detail: det[id] || {} }))
      .sort((a, b) => (a.detail.name || "").localeCompare(b.detail.name || "", "pt"));
  }

  // ---------------- UI: cesta no header + painel lateral ----------------

  let opened = false;

  function badge() {
    const n = countItens();
    const $b = document.getElementById("cartBtn");
    const $c = document.getElementById("cartCount");
    if ($b) $b.classList.toggle("has-items", n > 0);
    if ($c) $c.textContent = n;
  }

  function rowHtml({ id, qty, detail }) {
    return `
      <div class="cart-item">
        <div class="cart-item-img">${detail.imagem_url ? `<img class="cart-item-thumb" src="${UI.escapeHtml(detail.imagem_url)}" alt="">` : `<span class="cart-item-ph">·</span>`}</div>
        <div class="cart-item-body">
          <p class="cart-item-name">${UI.escapeHtml(detail.name || "Produto #" + id)}</p>
          ${detail.spec ? `<p class="cart-item-spec">${UI.escapeHtml(detail.spec)}</p>` : ""}
          ${detail.brand ? `<p class="cart-item-brand">${UI.escapeHtml(detail.brand)}</p>` : ""}
          <div class="cart-item-ctrls">
            <button class="cart-stepper" data-minus="${id}" type="button">–</button>
            <input class="cart-qty" type="number" min="0" step="1" value="${qty}" data-id="${id}">
            <button class="cart-stepper" data-plus="${id}" type="button">+</button>
            <span class="cart-item-price">${detail.price ? UI.fmtMoney(detail.price) : "—"}</span>
          </div>
        </div>
        <button class="cart-item-rm" data-rm="${id}" type="button" title="Remover">×</button>
      </div>`;
  }

  function renderPanel() {
    const items = list();
    const $list = document.getElementById("cartList");
    const $total = document.getElementById("cartTotal");
    const $vazio = document.getElementById("cartVazio");
    if (!$list) return;
    if (!items.length) {
      $list.innerHTML = "";
      if ($vazio) $vazio.style.display = "";
      if ($total) $total.textContent = UI.fmtMoney(0);
      return;
    }
    if ($vazio) $vazio.style.display = "none";
    $list.innerHTML = items.map(rowHtml).join("");
    if ($total) $total.textContent = UI.fmtMoney(totalValor());
    $list.querySelectorAll("[data-minus]").forEach((b) => {
      b.onclick = () => setQty(Number(b.dataset.minus), (itens()[b.dataset.minus] || 0) - 1);
    });
    $list.querySelectorAll("[data-plus]").forEach((b) => {
      b.onclick = () => setQty(Number(b.dataset.plus), (itens()[b.dataset.plus] || 0) + 1);
    });
    $list.querySelectorAll(".cart-qty").forEach((i) => {
      i.onchange = () => setQty(Number(i.dataset.id), Math.max(0, parseInt(i.value, 10) || 0));
    });
    $list.querySelectorAll("[data-rm]").forEach((b) => {
      b.onclick = () => remove(Number(b.dataset.rm));
    });
  }

  function toggle(force) {
    const $overlay = document.getElementById("cartOverlay");
    if (!$overlay) return;
    opened = force != null ? force : !opened;
    $overlay.classList.toggle("is-open", opened);
    document.body.style.overflow = opened ? "hidden" : "";
    if (opened) renderPanel();
  }

  // ---------------- sidebar fixa (catálogo 70/30) ----------------

  let sbScope = null;

  function refillS() {
    if (!sbScope) return;
    const $list = sbScope.querySelector(".cart-list");
    const $vazio = sbScope.querySelector(".cart-vazio");
    const $total = sbScope.querySelector(".cart-total-strong");
    const $info = sbScope.querySelector(".cart-sidebar-count");
    if (!$list) return;
    const items = list();
    if (!items.length) {
      $list.innerHTML = "";
      if ($vazio) $vazio.style.display = "";
      if ($total) $total.textContent = UI.fmtMoney(0);
    } else {
      if ($vazio) $vazio.style.display = "none";
      $list.innerHTML = items.map(rowHtml).join("");
      if ($total) $total.textContent = UI.fmtMoney(totalValor());
    }
    if ($info) $info.textContent = `${countItens()} item(ns) · ${totalQtd()} unidade(s)`;
    $list.querySelectorAll("[data-minus]").forEach((b) => {
      b.onclick = () => setQty(Number(b.dataset.minus), (itens()[b.dataset.minus] || 0) - 1);
    });
    $list.querySelectorAll("[data-plus]").forEach((b) => {
      b.onclick = () => setQty(Number(b.dataset.plus), (itens()[b.dataset.plus] || 0) + 1);
    });
    $list.querySelectorAll(".cart-qty").forEach((i) => {
      i.onchange = () => setQty(Number(i.dataset.id), Math.max(0, parseInt(i.value, 10) || 0));
    });
    $list.querySelectorAll("[data-rm]").forEach((b) => {
      b.onclick = () => remove(Number(b.dataset.rm));
    });
  }

  function mountSidebar(container) {
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
    sbScope = container.querySelector(".cart-sidebar");
    sbScope.querySelector("#sbLimpar").onclick = async () => {
      if (!(await UI.confirmDialog("Limpar todos os itens do carrinho?"))) return;
      clear();
    };
    sbScope.querySelector("#sbWhats").onclick = enviarWhatsapp;
    sbScope.querySelector("#sbPdf").onclick = gerarPdf;
    sbScope.querySelector("#sbCriar").onclick = () => criarCotacao(sbScope.querySelector("#sbCriar"));
    refillS();
    syncBtn();
  }

  function syncBtn() {
    const $btn = document.getElementById("cartBtn");
    if (!$btn) return;
    const hidden = !!document.querySelector(".cart-sidebar");
    $btn.style.display = hidden ? "none" : "";
  }

  // ---------------- exportação ----------------

  function mensagemWhatsapp() {
    const items = list();
    if (!items.length) return "";
    const linhas = ["*PEDIDO DE COTAÇÃO*", "Itens selecionados:"];
    items.forEach(({ qty, detail }, i) => {
      const specs = [];
      if (detail.spec) specs.push(detail.spec);
      if (detail.brand) specs.push(detail.brand);
      const extra = specs.length ? ` (${specs.join(" · ")})` : "";
      const preco = detail.price ? ` — ${UI.fmtMoney(detail.price)}` : "";
      linhas.push(`${i + 1}. ${detail.name || "Produto"}${extra} — qtd: ${qty}${preco}`);
    });
    const total = items.reduce((s, { qty, detail }) => s + (detail.price || 0) * qty, 0);
    linhas.push(`*Total estimado: ${UI.fmtMoney(total)}*`);
    linhas.push("");
    linhas.push("Aguardando melhor preço.");
    return linhas.join("\n");
  }

  function apenasDigitos(s) {
    return String(s || "").replace(/\D/g, "");
  }

  async function enviarWhatsapp() {
    const msg = mensagemWhatsapp();
    if (!msg) {
      UI.toast("Seu carrinho está vazio", "error");
      return;
    }
    let comNumero = [];
    try {
      comNumero = (await Api.listarFornecedores(true)).filter((f) => apenasDigitos(f.whatsapp));
    } catch (e) {}

    if (!comNumero.length) {
      window.open("https://wa.me/?text=" + encodeURIComponent(msg), "_blank", "noopener");
      return;
    }

    UI.openModal(
      `<div class="modal-head"><h3>Enviar para qual fornecedor?</h3><button class="icon-btn" data-close>×</button></div>
       <div class="wa-forn-list">
         ${comNumero.map((f) => `<button type="button" class="btn wa-forn-btn" data-forn="${f.id}">${UI.escapeHtml(f.nome)}</button>`).join("")}
         <button type="button" class="btn btn--ghost wa-forn-btn" data-outro>Outro contato (escolher no WhatsApp)</button>
       </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          modal.querySelector("[data-outro]").onclick = () => {
            UI.closeModal();
            window.open("https://wa.me/?text=" + encodeURIComponent(msg), "_blank", "noopener");
          };
          modal.querySelectorAll("[data-forn]").forEach((b) => {
            b.onclick = () => {
              const f = comNumero.find((x) => String(x.id) === b.dataset.forn);
              UI.closeModal();
              if (!f) return;
              window.open(`https://wa.me/${apenasDigitos(f.whatsapp)}?text=` + encodeURIComponent(msg), "_blank", "noopener");
            };
          });
        },
      }
    );
  }

  function gerarPdf() {
    const items = list();
    if (!items.length) {
      UI.toast("Seu carrinho está vazio", "error");
      return;
    }
    const w = window.open("", "_blank", "noopener");
    if (!w) {
      UI.toast("Bloqueio de pop-up: permita abrir novas janelas", "error");
      return;
    }
    const hoje = new Date().toLocaleDateString("pt-BR");
    const rows = items.map(({ qty, detail }, i) => `
      <tr>
        <td class="num">${i + 1}</td>
        <td>
          <div class="item-nome">${UI.escapeHtml(detail.name || "Produto #" + detail.id || "")}</div>
          ${detail.spec ? `<div class="item-spec">${UI.escapeHtml(detail.spec)}</div>` : ""}
          ${detail.brand ? `<div class="item-brand">${UI.escapeHtml(detail.brand)}</div>` : ""}
        </td>
        <td class="qtd">${qty}</td>
        <td class="preco">${detail.price ? UI.fmtMoney(detail.price) : "—"}</td>
        <td class="preco">${detail.price ? UI.fmtMoney(detail.price * qty) : "—"}</td>
      </tr>`).join("");
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
    <tfoot><tr class="total-row"><td colspan="4">Total estimado</td><td class="preco">${UI.fmtMoney(total)}</td></tr></tfoot>
  </table>
  <div class="rodape">Valores estimados para comparação entre distribuidores. Sujeito à confirmação de preço e disponibilidade.</div>
  <script>window.onload = function(){ window.print(); };<\/script>
</body>
</html>`);
    w.document.close();
  }

  function setLoading(btn, on) {
    if (!btn) return;
    btn.disabled = on;
    btn.classList.toggle("is-loading", on);
    if (on) {
      btn.dataset.label = btn.textContent.trim();
      btn.innerHTML = `<span class="spinner" aria-hidden="true"></span> Processando...`;
    } else {
      btn.innerHTML = btn.dataset.label || btn.innerHTML;
      delete btn.dataset.label;
    }
  }

  // ---------------- criar cotação (RFQ) ----------------

  async function criarCotacao(btn) {
    const itens = list();
    if (!itens.length) {
      UI.toast("Adicione pelo menos um item para criar a cotação", "error");
      return;
    }
    const payloadItens = itens.map(({ id, qty, detail }) => ({
      produto_id: id,
      variante_id: id,
      quantidade: qty,
      preco_estimado: detail.price != null ? Number(detail.price) : null,
    }));

    setLoading(btn, true);
    try {
      let fornecedores = [];
      try {
        fornecedores = await Api.listarFornecedores(true);
      } catch (e) {}
      const fornecedoresHtml = fornecedores.length
        ? fornecedores.map((f) => `
            <label style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:13.5px;">
              <input type="checkbox" name="fornecedor" value="${f.id}">
              ${UI.escapeHtml(f.nome)}
            </label>`).join("")
        : `<p style="font-size:13px;color:var(--ink-soft);">Nenhum fornecedor cadastrado ainda. Você pode criar a cotação mesmo assim e convidar fornecedores depois.</p>`;

      UI.openModal(
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
            modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
            modal.querySelector("#btnConfirmarCriar").onclick = async () => {
              const fornecedor_ids = [...modal.querySelectorAll('input[name="fornecedor"]:checked')].map((el) => Number(el.value));
              if (!payloadItens.length) { UI.toast("Adicione pelo menos um item para criar a cotação", "error"); return; }
              const $confirm = modal.querySelector("#btnConfirmarCriar");
              setLoading($confirm, true);
              try {
                const res = await Api.criarCotacao({
                  titulo: modal.querySelector("#mTitulo").value.trim() || null,
                  cliente: modal.querySelector("#mCliente").value.trim() || null,
                  observacoes: modal.querySelector("#mObs").value.trim() || null,
                  fornecedor_ids,
                  itens: payloadItens.map(({ produto_id, quantidade }) => ({ produto_id, quantidade })),
                });
                clear();
                UI.closeModal();
                UI.toast(`Cotação nº ${res.numero} criada`, "success");
                location.hash = `#/cotacoes/${res.id}`;
              } catch (e) {
                UI.toast("Erro ao criar cotação: " + e.message, "error");
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

  // ---------------- init ----------------

  function init() {
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

      $panel.querySelector("#cartClose").onclick = () => toggle(false);
      $panel.addEventListener("click", (e) => { if (e.target === $panel) toggle(false); });
      $panel.querySelector("#cartWhats").onclick = enviarWhatsapp;
      $panel.querySelector("#cartPdf").onclick = gerarPdf;
      $panel.querySelector("#cartCriar").onclick = () => criarCotacao($panel.querySelector("#cartCriar"));
      $panel.querySelector("#cartLimpar").onclick = async () => {
        if (!(await UI.confirmDialog("Limpar todos os itens do carrinho?"))) return;
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return { load, addItem, setQty, remove, clear, countItens, totalQtd, totalValor, list, toggle, mountSidebar, criarCotacao, mensagemWhatsapp, enviarWhatsapp, gerarPdf };
})();
