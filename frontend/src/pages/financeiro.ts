import "../styles/estoque.css";
import { api, type CondicaoPagamento, type ContaPayload, type ContaPagar, type ContaReceber } from "../api/client";
import { escapeHtml, fmtDate, fmtMoney } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;
let abaAtiva = "caixa";

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  paint();
  await carregarAba();
}

function paint(): void {
  if (!currentApp) return;
  currentApp.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Financeiro</h1>
      <p class="page-sub">Caixa, contas a receber e contas a pagar.</p>
    </div>
    <div class="tab-bar">
      <button class="tab-btn ${abaAtiva === "caixa" ? "is-active" : ""}" data-aba="caixa">Caixa</button>
      <button class="tab-btn ${abaAtiva === "receber" ? "is-active" : ""}" data-aba="receber">Receber</button>
      <button class="tab-btn ${abaAtiva === "pagar" ? "is-active" : ""}" data-aba="pagar">Pagar</button>
      <button class="tab-btn ${abaAtiva === "condicoes" ? "is-active" : ""}" data-aba="condicoes">Condições</button>
      <button class="tab-btn ${abaAtiva === "centros" ? "is-active" : ""}" data-aba="centros">Centros Custo</button>
      <button class="tab-btn ${abaAtiva === "adiantamentos" ? "is-active" : ""}" data-aba="adiantamentos">Adiantamentos</button>
    </div>
    <div id="finContent" class="estq-content"></div>
  `;
  currentApp.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      abaAtiva = btn.dataset.aba || "caixa";
      paint();
      void carregarAba();
    });
  });
}

async function carregarAba(): Promise<void> {
  const $ct = currentApp?.querySelector<HTMLElement>("#finContent");
  if (!$ct) return;
  if (abaAtiva === "caixa") await renderCaixa($ct);
  else if (abaAtiva === "receber") await renderReceber($ct);
  else if (abaAtiva === "pagar") await renderPagar($ct);
  else if (abaAtiva === "condicoes") await renderCondicoes($ct);
  else if (abaAtiva === "centros") await renderCentros($ct);
  else if (abaAtiva === "adiantamentos") await renderAdiantamentos($ct);
}

// ──────────────────────────────────────────────────────────
//  Caixa
// ──────────────────────────────────────────────────────────

async function renderCaixa($ct: HTMLElement): Promise<void> {
  let saldo = 0;
  try {
    const r = await api.saldoCaixa();
    saldo = r.saldo;
  } catch { /* */ }
  $ct.innerHTML = `
    <div class="fin-caixa-top">
      <div class="fin-saldo-box">
        <span class="fin-saldo-label">Saldo do caixa</span>
        <span class="fin-saldo-valor">${fmtMoney(saldo)}</span>
      </div>
      <div class="fin-acoes-caixa">
        <button class="btn btn--accent" data-tipo="entrada">+ Entrada</button>
        <button class="btn btn--danger" data-tipo="saida">- Saída</button>
        <button class="btn btn--ghost" data-tipo="suprimento">Suprimento</button>
        <button class="btn btn--ghost" data-tipo="sangria">Sangria</button>
      </div>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Data</th><th>Tipo</th><th>Descrição</th><th>Valor</th><th>Saldo</th><th>Forma</th><th>Doc</th></tr></thead>
      <tbody id="finCaixaBody"><tr><td colspan="7" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelectorAll<HTMLElement>(".fin-acoes-caixa [data-tipo]").forEach((b) => {
    b.addEventListener("click", () => abrirModalCaixa(b.dataset.tipo!));
  });
  await carregarMovCaixa();
}

async function carregarMovCaixa(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#finCaixaBody");
  if (!$body) return;
  try {
    const res = await api.listarMovimentosCaixa({ limit: 50 });
    if (!res.length) { $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Nenhum movimento</td></tr>`; return; }
    $body.innerHTML = res.map((m) => `
      <tr>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(m.criado_em)}</td>
        <td><span class="badge badge--${m.tipo === "entrada" || m.tipo === "abertura" || m.tipo === "suprimento" ? "ok" : "erro"}">${m.tipo}</span></td>
        <td>${escapeHtml(m.descricao)}</td>
        <td><strong>${fmtMoney(m.valor)}</strong></td>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtMoney(m.saldo_posterior)}</td>
        <td>${m.forma_pagamento}</td>
        <td style="font-size:11px;font-family:var(--font-mono);">${escapeHtml(m.documento || "")}</td>
      </tr>`).join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalCaixa(tipo: string): void {
  const label = { entrada: "Entrada", saida: "Saída", suprimento: "Suprimento", sangria: "Sangria" }[tipo] || tipo;
  const formas = ["dinheiro", "pix", "credito", "debito", "boleto", "cheque", "outro"];
  const opts = formas.map((f) => `<option value="${f}">${f}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>${label}</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Descrição</label><input id="cxDesc" autocomplete="off"></div>
       <div class="field"><label>Valor</label><input id="cxValor" type="number" step="0.01" min="0.01" placeholder="0,00"></div>
       <div class="field"><label>Forma de pagamento</label><select id="cxForma">${opts}</select></div>
       <div class="field"><label>Documento (opcional)</label><input id="cxDoc" autocomplete="off"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="cxSalvar">Registrar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#cxSalvar")!.onclick = async () => {
          const desc = (m.querySelector<HTMLInputElement>("#cxDesc")?.value || "").trim();
          const valor = parseFloat((m.querySelector<HTMLInputElement>("#cxValor")?.value || "0").replace(",", "."));
          if (!desc || valor <= 0) { toast("Preencha descrição e valor", "error"); return; }
          try {
            await api.movimentarCaixa({
              tipo, descricao: desc, valor,
              forma_pagamento: m.querySelector<HTMLSelectElement>("#cxForma")?.value || "dinheiro",
              documento: (m.querySelector<HTMLInputElement>("#cxDoc")?.value || "").trim() || undefined,
            });
            toast("Movimento registrado", "success");
            closeModal();
            await carregarAba();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Contas a Receber
// ──────────────────────────────────────────────────────────

async function renderReceber($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaRec">Nova conta a receber</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Cliente</th><th>Descrição</th><th>Valor</th><th>Saldo</th><th>Vencimento</th><th>Status</th><th></th></tr></thead>
      <tbody id="finRecBody"><tr><td colspan="7" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaRec")!.addEventListener("click", () => abrirModalConta("receber"));
  await carregarReceber();
}

async function carregarReceber(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#finRecBody");
  if (!$body) return;
  try {
    const res = await api.listarReceber();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Nenhuma conta</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr>
        <td><strong>${escapeHtml(c.cliente)}</strong></td>
        <td>${escapeHtml(c.descricao)}</td>
        <td>${fmtMoney(c.valor)}</td>
        <td><strong>${fmtMoney(c.saldo)}</strong></td>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(c.data_vencimento)}</td>
        <td><span class="badge badge--${c.status === "pago" ? "ok" : c.status === "aberto" ? "muted" : "erro"}">${c.status}</span></td>
        <td class="cell-actions">
          ${c.status !== "pago" ? `<button class="btn btn--ghost btn--sm" data-rec="${c.id}">Receber</button>` : ""}
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-rec]").forEach((b) => {
      b.addEventListener("click", async () => {
        const c = res.find((x) => x.id === Number(b.dataset.rec));
        if (c) abrirModalReceber(c);
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalConta(tipo: "receber" | "pagar"): void {
  const label = tipo === "receber" ? "a Receber" : "a Pagar";
  openModal(
    `<div class="modal-head"><h3>Nova conta ${label}</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>${tipo === "receber" ? "Cliente" : "Fornecedor"}</label><input id="cNome" autocomplete="off"></div>
       <div class="field"><label>Descrição</label><input id="cDesc" autocomplete="off"></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Valor</label><input id="cValor" type="number" step="0.01" min="0.01"></div>
         <div class="field" style="flex:1"><label>Vencimento</label><input id="cVenc" type="date"></div>
       </div>
       <div class="field"><label>Documento</label><input id="cDoc" autocomplete="off"></div>
       <div class="field"><label>Observação</label><textarea id="cObs" rows="2"></textarea></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="cSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#cSalvar")!.onclick = async () => {
          const payload: ContaPayload = {
            [tipo === "receber" ? "cliente" : "fornecedor"]: (m.querySelector<HTMLInputElement>("#cNome")?.value || "").trim(),
            valor: parseFloat((m.querySelector<HTMLInputElement>("#cValor")?.value || "0").replace(",", ".")),
            data_vencimento: m.querySelector<HTMLInputElement>("#cVenc")?.value || "",
            descricao: (m.querySelector<HTMLInputElement>("#cDesc")?.value || "").trim(),
            documento: (m.querySelector<HTMLInputElement>("#cDoc")?.value || "").trim() || undefined,
            observacao: (m.querySelector<HTMLInputElement>("#cObs")?.value || "").trim() || undefined,
          };
          if (!payload.valor || !payload.data_vencimento || !(tipo === "receber" ? payload.cliente : payload.fornecedor)) {
            toast("Preencha nome, valor e vencimento", "error"); return;
          }
          try {
            if (tipo === "receber") await api.criarReceber(payload);
            else await api.criarPagar(payload);
            toast("Conta criada", "success"); closeModal(); await carregarAba();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

function abrirModalReceber(c: ContaReceber): void {
  openModal(
    `<div class="modal-head"><h3>Receber — ${escapeHtml(c.cliente)}</h3><button class="icon-btn" data-close>×</button></div>
     <p style="font-size:13px;color:var(--ink-soft);margin-bottom:12px;">Valor original: ${fmtMoney(c.valor)} · Saldo: ${fmtMoney(c.saldo)}</p>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Valor a receber</label><input id="rValor" type="number" step="0.01" min="0.01" value="${c.saldo}"></div>
       <div class="field"><label>Data do recebimento</label><input id="rData" type="date"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="rSalvar">Receber</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#rSalvar")!.onclick = async () => {
          const valor = parseFloat((m.querySelector<HTMLInputElement>("#rValor")?.value || "0").replace(",", "."));
          const data = m.querySelector<HTMLInputElement>("#rData")?.value || undefined;
          if (valor <= 0) { toast("Valor inválido", "error"); return; }
          try {
            await api.receberConta(c.id, { valor, data_recebimento: data });
            toast("Recebimento registrado", "success"); closeModal(); await carregarAba();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Contas a Pagar
// ──────────────────────────────────────────────────────────

async function renderPagar($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaPag">Nova conta a pagar</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Fornecedor</th><th>Descrição</th><th>Valor</th><th>Saldo</th><th>Vencimento</th><th>Status</th><th></th></tr></thead>
      <tbody id="finPagBody"><tr><td colspan="7" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaPag")!.addEventListener("click", () => abrirModalConta("pagar"));
  await carregarPagar();
}

async function carregarPagar(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#finPagBody");
  if (!$body) return;
  try {
    const res = await api.listarPagar();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Nenhuma conta</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr>
        <td><strong>${escapeHtml(c.fornecedor)}</strong></td>
        <td>${escapeHtml(c.descricao)}</td>
        <td>${fmtMoney(c.valor)}</td>
        <td><strong>${fmtMoney(c.saldo)}</strong></td>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(c.data_vencimento)}</td>
        <td><span class="badge badge--${c.status === "pago" ? "ok" : c.status === "aberto" ? "muted" : "erro"}">${c.status}</span></td>
        <td class="cell-actions">
          ${c.status !== "pago" ? `<button class="btn btn--ghost btn--sm" data-pag="${c.id}">Pagar</button>` : ""}
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-pag]").forEach((b) => {
      b.addEventListener("click", async () => {
        const c = res.find((x) => x.id === Number(b.dataset.pag));
        if (c) abrirModalPagar(c);
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalPagar(c: ContaPagar): void {
  openModal(
    `<div class="modal-head"><h3>Pagar — ${escapeHtml(c.fornecedor)}</h3><button class="icon-btn" data-close>×</button></div>
     <p style="font-size:13px;color:var(--ink-soft);margin-bottom:12px;">Valor original: ${fmtMoney(c.valor)} · Saldo: ${fmtMoney(c.saldo)}</p>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Valor a pagar</label><input id="pValor" type="number" step="0.01" min="0.01" value="${c.saldo}"></div>
       <div class="field"><label>Data do pagamento</label><input id="pData" type="date"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="pSalvar">Pagar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#pSalvar")!.onclick = async () => {
          const valor = parseFloat((m.querySelector<HTMLInputElement>("#pValor")?.value || "0").replace(",", "."));
          const data = m.querySelector<HTMLInputElement>("#pData")?.value || undefined;
          if (valor <= 0) { toast("Valor inválido", "error"); return; }
          try {
            await api.pagarConta(c.id, { valor, data_pagamento: data });
            toast("Pagamento registrado", "success"); closeModal(); await carregarAba();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Condições de Pagamento
// ──────────────────────────────────────────────────────────

async function renderCondicoes($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaCond">Nova condição</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Nome</th><th>Parcelas</th><th>Status</th><th></th></tr></thead>
      <tbody id="tblCondBody"><tr><td colspan="4" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>`;
  $ct.querySelector<HTMLElement>("#btnNovaCond")!.addEventListener("click", () => abrirModalCondicao(null));
  await carregarCondicoes();
}

async function carregarCondicoes(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblCondBody");
  if (!$body) return;
  try {
    const res = await api.listarCondicoes();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Nenhuma condição</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr>
        <td><strong>${escapeHtml(c.nome)}</strong>${c.descricao ? `<div style="font-size:12px;color:var(--ink-soft);">${escapeHtml(c.descricao)}</div>` : ""}</td>
        <td><button class="btn btn--ghost btn--sm" data-parcelas="${c.id}">Ver parcelas</button></td>
        <td><span class="badge badge--${c.ativo ? "ok" : "muted"}">${c.ativo ? "Ativa" : "Inativa"}</span></td>
        <td class="cell-actions">
          <button class="btn btn--ghost btn--sm" data-editar="${c.id}">Editar</button>
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-editar]").forEach((b) => {
      b.addEventListener("click", async () => {
        const c = res.find((x) => x.id === Number(b.dataset.editar));
        if (c) abrirModalCondicao(c);
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-parcelas]").forEach((b) => {
      b.addEventListener("click", async () => {
        const c = res.find((x) => x.id === Number(b.dataset.parcelas));
        if (c) {
          const det = await api.getCondicao(c.id);
          openModal(
            `<div class="modal-head"><h3>${escapeHtml(det.nome)} — Parcelas</h3><button class="icon-btn" data-close>×</button></div>
             <div class="table-wrap"><table class="data-table">
               <thead><tr><th>#</th><th>Dias</th><th>%</th></tr></thead>
               <tbody>${(det.parcelas || []).map((p) => `
                 <tr><td>${p.sequencia}</td><td>${p.dias}</td><td>${p.percentual}%</td></tr>`).join("")}
               </tbody></table></div>
             <div class="modal-actions"><button class="btn" data-close>Fechar</button></div>`,
            { onMount: (m) => { m.querySelectorAll("[data-close]").forEach((el) => ((el as HTMLElement).onclick = closeModal)); } }
          );
        }
      });
    });
  } catch { $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Erro</td></tr>`; }
}

function abrirModalCondicao(cond: CondicaoPagamento | null): void {
  const editando = !!cond;
  openModal(
    `<div class="modal-head"><h3>${editando ? "Editar" : "Nova"} condição</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Nome *</label><input id="coNome" value="${escapeHtml(cond?.nome || "")}"></div>
       <div class="field"><label>Descrição</label><input id="coDesc" value="${escapeHtml(cond?.descricao || "")}"></div>
       <div class="field"><label>Parcelas (sequência: dias,%) — uma por linha</label>
         <textarea id="coParcelas" rows="4" placeholder="Ex.:&#10;1:0,100&#10;2:30,50&#10;3:60,50"></textarea>
       </div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="coSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      async onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        if (editando && cond) {
          const det = await api.getCondicao(cond.id);
          const txt = (det.parcelas || []).map((p) => `${p.sequencia}:${p.dias},${p.percentual}`).join("\n");
          m.querySelector<HTMLTextAreaElement>("#coParcelas")!.value = txt;
        }
        m.querySelector<HTMLElement>("#coSalvar")!.onclick = async () => {
          const nome = (m.querySelector<HTMLInputElement>("#coNome")?.value || "").trim();
          if (!nome) { toast("Informe o nome", "error"); return; }
          try {
            if (editando && cond) await api.atualizarCondicao(cond.id, { nome, descricao: m.querySelector<HTMLInputElement>("#coDesc")?.value || "" });
            else {
              const r = await api.criarCondicao({ nome, descricao: m.querySelector<HTMLInputElement>("#coDesc")?.value || "" });
              cond = { id: r.id, nome, descricao: "", ativo: true };
            }
            const txt = (m.querySelector<HTMLTextAreaElement>("#coParcelas")?.value || "").trim();
            const parcelas = txt.split("\n").filter(Boolean).map((linha) => {
              const [seq, resto] = linha.split(":");
              const [dias, pct] = (resto || "").split(",");
              return { sequencia: parseInt(seq, 10), dias: parseInt(dias, 10), percentual: parseFloat(pct.replace(",", ".")) };
            }).filter((p) => p.sequencia > 0);
            if (parcelas.length) await api.salvarParcelas(cond!.id, parcelas);
            toast(editando ? "Condição atualizada" : "Condição criada", "success");
            closeModal();
            await carregarCondicoes();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Centros de Custo
// ──────────────────────────────────────────────────────────

async function renderCentros($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovoCC">Novo centro</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Código</th><th>Nome</th><th>Status</th></tr></thead>
      <tbody id="tblCCBody"><tr><td colspan="3" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>`;
  $ct.querySelector<HTMLElement>("#btnNovoCC")!.addEventListener("click", () => {
    openModal(
      `<div class="modal-head"><h3>Novo centro de custo</h3><button class="icon-btn" data-close>×</button></div>
       <div class="field-row" style="flex-direction:column;gap:10px;">
         <div class="field"><label>Código</label><input id="ccCodigo"></div>
         <div class="field"><label>Nome</label><input id="ccNome"></div>
       </div>
       <div class="modal-actions">
         <button class="btn btn--accent" id="ccSalvar">Salvar</button>
         <button class="btn" data-close>Cancelar</button>
       </div>`,
      {
        onMount(m) {
          m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
          m.querySelector<HTMLElement>("#ccSalvar")!.onclick = async () => {
            try {
              await api.criarCentroCusto({
                codigo: (m.querySelector<HTMLInputElement>("#ccCodigo")?.value || "").trim(),
                nome: (m.querySelector<HTMLInputElement>("#ccNome")?.value || "").trim(),
              });
              toast("Centro criado", "success"); closeModal(); await carregarCentros();
            } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
          };
        },
      }
    );
  });
  await carregarCentros();
}

async function carregarCentros(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblCCBody");
  if (!$body) return;
  try {
    const res = await api.listarCentrosCusto();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="3" class="pdv-sem-res">Nenhum centro</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr><td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(c.codigo)}</td><td>${escapeHtml(c.nome)}</td>
      <td><span class="badge badge--${c.ativo ? "ok" : "muted"}">${c.ativo ? "Ativo" : "Inativo"}</span></td></tr>`).join("");
  } catch { $body.innerHTML = `<tr><td colspan="3" class="pdv-sem-res">Erro</td></tr>`; }
}

// ─── Adiantamentos ─────────────────────────────────────────

async function renderAdiantamentos($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `<p><button class="btn btn--accent" id="btnNovoAdiant">Novo adiantamento</button></p>
    <div class="table-wrap"><table class="data-table"><thead><tr><th>Tipo</th><th>Pessoa</th><th>Valor</th><th>Saldo</th><th>Data</th></tr></thead>
    <tbody id="tblAdiantBody"><tr><td colspan="5" class="pdv-sem-res">Carregando…</td></tr></tbody></table></div>`;
  $ct.querySelector<HTMLElement>("#btnNovoAdiant")!.addEventListener("click", () => abrirModalAdiantamento());
  const $body = $ct.querySelector<HTMLElement>("#tblAdiantBody")!;
  try {
    const r = await api.listarAdiantamentos();
    if (!r.length) { $body.innerHTML = `<tr><td colspan="5" class="pdv-sem-res">Nenhum</td></tr>`; return; }
    $body.innerHTML = r.map((a) => `<tr><td><span class="badge badge--muted">${a.tipo}</span></td><td><strong>${escapeHtml(a.pessoa_nome)}</strong></td><td>${fmtMoney(a.valor)}</td><td><strong>${fmtMoney(a.saldo)}</strong></td><td style="font-size:12px;color:var(--ink-soft);">${fmtDate(a.data_adiantamento)}</td></tr>`).join("");
  } catch { $body.innerHTML = `<tr><td colspan="5" class="pdv-sem-res">Erro</td></tr>`; }
}

function abrirModalAdiantamento(): void {
  openModal(
    `<div class="modal-head"><h3>Novo adiantamento</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Tipo</label><select id="adTipo"><option value="cliente">Cliente</option><option value="fornecedor">Fornecedor</option></select></div>
       <div class="field"><label>Nome</label><input id="adNome"></div>
       <div class="field"><label>Valor</label><input id="adValor" type="number" step="0.01"></div>
       <div class="field"><label>Data</label><input id="adData" type="date"></div>
       <div class="field"><label>Observação</label><textarea id="adObs" rows="2"></textarea></div>
     </div>
     <div class="modal-actions"><button class="btn btn--accent" id="adSalvar">Salvar</button><button class="btn" data-close>Cancelar</button></div>`,
    { onMount(m) {
      m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
      m.querySelector<HTMLElement>("#adSalvar")!.onclick = async () => {
        try {
          await api.criarAdiantamento({
            tipo: m.querySelector<HTMLSelectElement>("#adTipo")!.value,
            pessoa_nome: (m.querySelector<HTMLInputElement>("#adNome")?.value || "").trim(),
            valor: parseFloat((m.querySelector<HTMLInputElement>("#adValor")?.value || "0").replace(",", ".")),
            data_adiantamento: m.querySelector<HTMLInputElement>("#adData")?.value || "",
            observacao: (m.querySelector<HTMLInputElement>("#adObs")?.value || "").trim() || undefined,
          });
          toast("Adiantamento criado", "success"); closeModal(); location.reload();
        } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
      };
    }}
  );
}
