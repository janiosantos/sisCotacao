import "../styles/estoque.css";
import { api, type Deposito, type LotePayload, type MovimentoPayload } from "../api/client";
import { escapeHtml, fmtDate, fmtMoney } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;
let abaAtiva = "saldo";
let depositos: Deposito[] = [];

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  depositos = [];
  paint();
  await carregarDepositos();
  await carregarAba();
}

function paint(): void {
  if (!currentApp) return;
  currentApp.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Estoque</h1>
      <p class="page-sub">Saldo, depósitos, movimentos e lotes.</p>
    </div>
    <div class="tab-bar">
      <button class="tab-btn ${abaAtiva === "saldo" ? "is-active" : ""}" data-aba="saldo">Saldo</button>
      <button class="tab-btn ${abaAtiva === "depositos" ? "is-active" : ""}" data-aba="depositos">Depósitos</button>
      <button class="tab-btn ${abaAtiva === "movimentos" ? "is-active" : ""}" data-aba="movimentos">Movimentos</button>
      <button class="tab-btn ${abaAtiva === "lotes" ? "is-active" : ""}" data-aba="lotes">Lotes</button>
      <button class="tab-btn ${abaAtiva === "expedicao" ? "is-active" : ""}" data-aba="expedicao">Expedição</button>
    </div>
    <div id="estqContent" class="estq-content"></div>
  `;
  currentApp.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      abaAtiva = btn.dataset.aba || "saldo";
      paint();
      void carregarAba();
    });
  });
}

async function carregarDepositos(): Promise<void> {
  try {
    depositos = await api.listarDepositos();
  } catch { /* silêncio */ }
}

async function carregarAba(): Promise<void> {
  const $ct = currentApp?.querySelector<HTMLElement>("#estqContent");
  if (!$ct) return;
  if (abaAtiva === "saldo") await renderSaldo($ct);
  else if (abaAtiva === "depositos") await renderDepositos($ct);
  else if (abaAtiva === "movimentos") await renderMovimentos($ct);
  else if (abaAtiva === "lotes") await renderLotes($ct);
  else if (abaAtiva === "expedicao") await renderExpedicao($ct);
}

// ──────────────────────────────────────────────────────────
//  Saldo
// ──────────────────────────────────────────────────────────

async function renderSaldo($ct: HTMLElement): Promise<void> {
  const depOpts = depositos.map((d) => `<option value="${d.id}">${escapeHtml(d.nome)}</option>`).join("");
  $ct.innerHTML = `
    <div class="estq-filtros">
      <div class="field"><label>Depósito</label>
        <select id="filtroDep">${depOpts}</select>
      </div>
      <div class="field"><label>Busca</label><input id="filtroQ" placeholder="Produto, SKU, marca…" autocomplete="off"></div>
      <button class="btn btn--accent" id="btnFiltrar">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table" id="tblSaldo">
      <thead><tr><th>Produto</th><th>SKU</th><th>Depósito</th><th>Qtd.</th><th>Preço</th><th>Atualizado</th></tr></thead>
      <tbody id="tblSaldoBody"><tr><td colspan="6" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnFiltrar")!.addEventListener("click", () => void buscarSaldo());
  $ct.querySelector<HTMLInputElement>("#filtroQ")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") void buscarSaldo();
  });
  await buscarSaldo();
}

async function buscarSaldo(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblSaldoBody");
  if (!$body) return;
  const deposito_id = (currentApp?.querySelector<HTMLSelectElement>("#filtroDep")?.value || "").trim();
  const q = (currentApp?.querySelector<HTMLInputElement>("#filtroQ")?.value || "").trim();
  try {
    const res = await api.saldoEstoque({ deposito_id: deposito_id || undefined, q: q || undefined });
    if (!res.length) {
      $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Nenhum saldo encontrado</td></tr>`;
      return;
    }
    $body.innerHTML = res
      .map(
        (s) => `
        <tr>
          <td><strong>${escapeHtml(s.produto_nome)}</strong>${s.marca ? `<div style="font-size:11px;color:var(--ink-faint);">${escapeHtml(s.marca)}</div>` : ""}</td>
          <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(s.sku)}</td>
          <td>${escapeHtml(s.deposito_nome)}</td>
          <td><strong>${s.quantidade}</strong></td>
          <td>${fmtMoney(s.preco)}</td>
          <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(s.atualizado_em)}</td>
        </tr>`
      )
      .join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Erro ao carregar saldo</td></tr>`;
  }
}

// ──────────────────────────────────────────────────────────
//  Depósitos
// ──────────────────────────────────────────────────────────

async function renderDepositos($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovoDep">Novo depósito</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Nome</th><th>Ativo</th><th>Criado em</th><th></th></tr></thead>
      <tbody id="tblDepBody"><tr><td colspan="4" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovoDep")!.addEventListener("click", () => abrirModalDeposito(null));
  await carregarTabelaDep();
}

async function carregarTabelaDep(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblDepBody");
  if (!$body) return;
  try {
    const res = await api.listarDepositos();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Nenhum depósito</td></tr>`; return; }
    $body.innerHTML = res
      .map(
        (d) => `
        <tr>
          <td><strong>${escapeHtml(d.nome)}</strong></td>
          <td><span class="badge badge--${d.ativo ? "ok" : "muted"}">${d.ativo ? "Ativo" : "Inativo"}</span></td>
          <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(d.criado_em)}</td>
          <td class="cell-actions">
            <button class="btn btn--ghost btn--sm" data-editar="${d.id}">Editar</button>
            <button class="btn btn--ghost btn--sm" data-toggle="${d.id}">${d.ativo ? "Desativar" : "Ativar"}</button>
          </td>
        </tr>`
      )
      .join("");
    $body.querySelectorAll<HTMLElement>("[data-editar]").forEach((b) => {
      b.addEventListener("click", () => {
        const d = res.find((x) => x.id === Number(b.dataset.editar));
        if (d) abrirModalDeposito(d);
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
      b.addEventListener("click", async () => {
        const d = res.find((x) => x.id === Number(b.dataset.toggle));
        if (d) {
          await api.alternarAtivoDeposito(d.id, !d.ativo);
          await carregarTabelaDep();
          await carregarDepositos();
        }
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalDeposito(dep: Deposito | null): void {
  const editando = dep !== null;
  openModal(
    `<div class="modal-head"><h3>${editando ? "Editar" : "Novo"} depósito</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field"><label>Nome</label><input id="depNome" value="${escapeHtml(dep?.nome || "")}" autocomplete="off"></div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="depSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("#depSalvar")!.onclick = async () => {
          const nome = (modal.querySelector<HTMLInputElement>("#depNome")?.value || "").trim();
          if (!nome) { toast("Informe o nome", "error"); return; }
          try {
            if (editando) await api.atualizarDeposito(dep!.id, nome);
            else await api.criarDeposito(nome);
            toast(editando ? "Depósito atualizado" : "Depósito criado", "success");
            closeModal();
            await carregarTabelaDep();
            await carregarDepositos();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
        setTimeout(() => modal.querySelector<HTMLInputElement>("#depNome")?.focus(), 0);
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Movimentos
// ──────────────────────────────────────────────────────────

async function renderMovimentos($ct: HTMLElement): Promise<void> {
  const depOpts = depositos.map((d) => `<option value="${d.id}">${escapeHtml(d.nome)}</option>`).join("");
  $ct.innerHTML = `
    <div class="estq-filtros">
      <p><button class="btn btn--accent" id="btnNovoMov">Registrar movimento</button></p>
      <div class="field"><label>Depósito</label>
        <select id="filtroMovDep"><option value="">Todos</option>${depOpts}</select>
      </div>
      <div class="field"><label>Tipo</label>
        <select id="filtroMovTipo"><option value="">Todos</option><option value="entrada">Entrada</option><option value="saida">Saída</option><option value="ajuste">Ajuste</option></select>
      </div>
      <button class="btn btn--ghost" id="btnFiltrarMov">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Data</th><th>Produto</th><th>Depósito</th><th>Tipo</th><th>Qtd</th><th>Saldo ant.</th><th>Saldo novo</th><th>Doc</th></tr></thead>
      <tbody id="tblMovBody"><tr><td colspan="8" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovoMov")!.addEventListener("click", () => abrirModalMovimento());
  $ct.querySelector<HTMLElement>("#btnFiltrarMov")!.addEventListener("click", () => void buscarMovimentos());
  await buscarMovimentos();
}

async function buscarMovimentos(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblMovBody");
  if (!$body) return;
  const deposito_id = (currentApp?.querySelector<HTMLSelectElement>("#filtroMovDep")?.value || "").trim();
  const tipo = (currentApp?.querySelector<HTMLSelectElement>("#filtroMovTipo")?.value || "").trim();
  try {
    const res = await api.listarMovimentos({ deposito_id: deposito_id || undefined, tipo: tipo || undefined });
    if (!res.length) { $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Nenhum movimento</td></tr>`; return; }
    $body.innerHTML = res
      .map(
        (m) => `
        <tr>
          <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(m.criado_em)}</td>
          <td><strong>${escapeHtml(m.produto_nome)}</strong><div style="font-size:11px;color:var(--ink-faint);">${escapeHtml(m.sku)}</div></td>
          <td>${escapeHtml(m.deposito_nome)}</td>
          <td><span class="badge badge--${m.tipo === "entrada" ? "ok" : m.tipo === "saida" ? "erro" : "muted"}">${m.tipo}</span></td>
          <td><strong>${m.quantidade}</strong></td>
          <td style="font-size:12px;color:var(--ink-soft);">${m.saldo_anterior}</td>
          <td style="font-size:12px;color:var(--ink-soft);">${m.saldo_posterior}</td>
          <td style="font-size:12px;font-family:var(--font-mono);">${escapeHtml(m.documento || "")}</td>
        </tr>`
      )
      .join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalMovimento(): void {
  const depOpts = depositos.map((d) => `<option value="${d.id}">${escapeHtml(d.nome)}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>Registrar movimento</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Depósito</label><select id="movDep">${depOpts}</select></div>
       <div class="field"><label>Tipo</label>
         <select id="movTipo"><option value="entrada">Entrada</option><option value="saida">Saída</option><option value="ajuste">Ajuste</option></select>
       </div>
       <div class="field"><label>Produto (ID)</label><input id="movVarId" type="number" min="1" placeholder="ID da variante"></div>
       <div class="field"><label>Quantidade</label><input id="movQtd" type="number" min="0.01" step="any" placeholder="1"></div>
       <div class="field"><label>Documento (opcional)</label><input id="movDoc" placeholder="NF, requisição…" autocomplete="off"></div>
       <div class="field"><label>Observação</label><textarea id="movObs" rows="2"></textarea></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="movSalvar">Registrar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("#movSalvar")!.onclick = async () => {
          const payload: MovimentoPayload = {
            deposito_id: parseInt((modal.querySelector<HTMLSelectElement>("#movDep")?.value || "0"), 10),
            tipo: (modal.querySelector<HTMLSelectElement>("#movTipo")?.value || "entrada") as MovimentoPayload["tipo"],
            variante_id: parseInt((modal.querySelector<HTMLInputElement>("#movVarId")?.value || "0"), 10),
            quantidade: parseFloat((modal.querySelector<HTMLInputElement>("#movQtd")?.value || "0").replace(",", ".")),
            documento: (modal.querySelector<HTMLInputElement>("#movDoc")?.value || "").trim() || undefined,
            observacao: (modal.querySelector<HTMLInputElement>("#movObs")?.value || "").trim() || undefined,
          };
          if (!payload.deposito_id || !payload.variante_id || payload.quantidade <= 0) {
            toast("Preencha depósito, produto e quantidade", "error"); return;
          }
          try {
            await api.registrarMovimento(payload);
            toast("Movimento registrado", "success");
            closeModal();
            await buscarMovimentos();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ─── Expedição ─────────────────────────────────────────────

async function renderExpedicao($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `<p><button class="btn btn--accent" id="btnNovaExp">Nova expedição</button></p>
    <div class="table-wrap"><table class="data-table"><thead><tr><th>Código</th><th>Depósito</th><th>Data</th><th>Transportadora</th><th>Status</th><th></th></tr></thead>
    <tbody id="tblExpBody"><tr><td colspan="6" class="pdv-sem-res">Carregando…</td></tr></tbody></table></div>`;
  $ct.querySelector<HTMLElement>("#btnNovaExp")!.addEventListener("click", () => {
    openModal(
      `<div class="modal-head"><h3>Nova expedição</h3><button class="icon-btn" data-close>×</button></div>
       <div class="field-row" style="flex-direction:column;gap:10px;">
         <div class="field"><label>Código</label><input id="exCodigo" placeholder="EXP-001"></div>
         <div class="field"><label>Depósito ID</label><input id="exDep" type="number" min="1"></div>
         <div class="field"><label>Transportadora</label><input id="exTransp"></div>
         <div class="field"><label>Observação</label><textarea id="exObs" rows="2"></textarea></div>
       </div>
       <div class="modal-actions"><button class="btn btn--accent" id="exSalvar">Salvar</button><button class="btn" data-close>Cancelar</button></div>`,
      { onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#exSalvar")!.onclick = async () => {
          try {
            await api.criarExpedicao({
              codigo: (m.querySelector<HTMLInputElement>("#exCodigo")?.value || "").trim(),
              deposito_id: parseInt(m.querySelector<HTMLInputElement>("#exDep")?.value || "0", 10),
              transportadora: (m.querySelector<HTMLInputElement>("#exTransp")?.value || "").trim() || undefined,
              observacao: (m.querySelector<HTMLInputElement>("#exObs")?.value || "").trim() || undefined,
            });
            toast("Expedição criada", "success"); closeModal(); location.reload();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      }}
    );
  });
  const $body = $ct.querySelector<HTMLElement>("#tblExpBody")!;
  try {
    const r = await api.listarExpedicao();
    if (!r.length) { $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Nenhuma</td></tr>`; return; }
    const statusOpts = ["pendente", "separando", "conferido", "carregado", "finalizado"];
    $body.innerHTML = r.map((e) => `<tr>
      <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(e.codigo)}</td>
      <td>${escapeHtml(e.deposito_nome)}</td>
      <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(e.data_expedicao)}</td>
      <td>${escapeHtml(e.transportadora || "—")}</td>
      <td><span class="badge badge--${e.status === "finalizado" ? "ok" : "muted"}">${e.status}</span></td>
      <td class="cell-actions">
        <select data-status="${e.id}" style="font-size:12px;padding:2px 4px;">
          ${statusOpts.map((s) => `<option value="${s}" ${s === e.status ? "selected" : ""}>${s}</option>`).join("")}
        </select>
        <button class="btn btn--ghost btn--sm" data-atualizar="${e.id}" title="Atualizar">✓</button>
      </td></tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-atualizar]").forEach((b) => {
      b.addEventListener("click", async () => {
        const sel = (b.closest("td") as HTMLElement)?.querySelector<HTMLSelectElement>("[data-status]");
        if (sel) { await api.atualizarStatusExpedicao(Number(b.dataset.atualizar), sel.value); location.reload(); }
      });
    });
  } catch { $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Erro</td></tr>`; }
}

// ──────────────────────────────────────────────────────────
//  Lotes
// ──────────────────────────────────────────────────────────

async function renderLotes($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovoLote">Novo lote</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Produto</th><th>Lote</th><th>Depósito</th><th>Qtd</th><th>Fabricação</th><th>Validade</th></tr></thead>
      <tbody id="tblLoteBody"><tr><td colspan="6" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovoLote")!.addEventListener("click", () => abrirModalLote(null));
  await carregarTabelaLotes();
}

async function carregarTabelaLotes(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblLoteBody");
  if (!$body) return;
  try {
    const res = await api.listarLotes();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Nenhum lote</td></tr>`; return; }
    $body.innerHTML = res
      .map(
        (l) => `
        <tr>
          <td><strong>${escapeHtml(l.produto_nome)}</strong><div style="font-size:11px;color:var(--ink-faint);">${escapeHtml(l.sku)}</div></td>
          <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(l.codigo)}</td>
          <td>${escapeHtml(l.deposito_nome)}</td>
          <td><strong>${l.quantidade}</strong></td>
          <td style="font-size:12px;color:var(--ink-soft);">${l.data_fabricacao ? fmtDate(l.data_fabricacao) : "—"}</td>
          <td style="font-size:12px;color:var(--ink-soft);">${l.data_validade ? fmtDate(l.data_validade) : "—"}</td>
        </tr>`
      )
      .join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalLote(_lote: LotePayload | null): void {
  const depOpts = depositos.map((d) => `<option value="${d.id}">${escapeHtml(d.nome)}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>Novo lote</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Depósito</label><select id="loteDep">${depOpts}</select></div>
       <div class="field"><label>Produto (ID da variante)</label><input id="loteVarId" type="number" min="1" placeholder="ID da variante"></div>
       <div class="field"><label>Código do lote</label><input id="loteCod" placeholder="Lote-001" autocomplete="off"></div>
       <div class="field"><label>Quantidade</label><input id="loteQtd" type="number" min="0" step="any" placeholder="0"></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Fabricação</label><input id="loteFab" type="date"></div>
         <div class="field" style="flex:1"><label>Validade</label><input id="loteVal" type="date"></div>
       </div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="loteSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("#loteSalvar")!.onclick = async () => {
          const payload: LotePayload = {
            deposito_id: parseInt((modal.querySelector<HTMLSelectElement>("#loteDep")?.value || "0"), 10),
            variante_id: parseInt((modal.querySelector<HTMLInputElement>("#loteVarId")?.value || "0"), 10),
            codigo: (modal.querySelector<HTMLInputElement>("#loteCod")?.value || "").trim(),
            quantidade: parseFloat((modal.querySelector<HTMLInputElement>("#loteQtd")?.value || "0").replace(",", ".")),
            data_fabricacao: (modal.querySelector<HTMLInputElement>("#loteFab")?.value || "") || undefined,
            data_validade: (modal.querySelector<HTMLInputElement>("#loteVal")?.value || "") || undefined,
          };
          if (!payload.deposito_id || !payload.variante_id || !payload.codigo) {
            toast("Preencha depósito, produto e código do lote", "error"); return;
          }
          try {
            await api.criarLote(payload);
            toast("Lote criado", "success");
            closeModal();
            await carregarTabelaLotes();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}
