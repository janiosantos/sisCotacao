import "../styles/estoque.css";
import { api, type CstCode, type FiscalConfigItem } from "../api/client";
import { escapeHtml, fmtDate, fmtMoney } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;
let abaAtiva = "cfop";

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  paint();
  await carregarAba();
}

function paint(): void {
  if (!currentApp) return;
  currentApp.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Fiscal</h1>
      <p class="page-sub">CFOP, CST e configuração tributária por produto.</p>
    </div>
    <div class="tab-bar">
      <button class="tab-btn ${abaAtiva === "cfop" ? "is-active" : ""}" data-aba="cfop">CFOP</button>
      <button class="tab-btn ${abaAtiva === "cst" ? "is-active" : ""}" data-aba="cst">CST</button>
      <button class="tab-btn ${abaAtiva === "config" ? "is-active" : ""}" data-aba="config">Config. Fiscal</button>
      <button class="tab-btn ${abaAtiva === "emitente" ? "is-active" : ""}" data-aba="emitente">Emitente</button>
      <button class="tab-btn ${abaAtiva === "nfe" ? "is-active" : ""}" data-aba="nfe">NF-e</button>
      <button class="tab-btn ${abaAtiva === "ibpt" ? "is-active" : ""}" data-aba="ibpt">IBPT</button>
    </div>
    <div id="fiscContent" class="estq-content"></div>
  `;
  currentApp.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      abaAtiva = btn.dataset.aba || "cfop";
      paint();
      void carregarAba();
    });
  });
}

async function carregarAba(): Promise<void> {
  const $ct = currentApp?.querySelector<HTMLElement>("#fiscContent");
  if (!$ct) return;
  if (abaAtiva === "cfop") await renderCfop($ct);
  else if (abaAtiva === "cst") await renderCst($ct);
  else if (abaAtiva === "config") await renderConfig($ct);
  else if (abaAtiva === "emitente") await renderEmitente($ct);
  else if (abaAtiva === "nfe") await renderNfe($ct);
  else if (abaAtiva === "ibpt") await renderIbpt($ct);
}

// ──────────────────────────────────────────────────────────
//  CFOP
// ──────────────────────────────────────────────────────────

async function renderCfop($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <div class="estq-filtros">
      <div class="field"><label>Tipo</label>
        <select id="filtroCfopTipo"><option value="">Todos</option><option value="entrada">Entrada</option><option value="saida">Saída</option><option value="mesma_uf">Mesma UF</option><option value="outra_uf">Outra UF</option></select>
      </div>
      <button class="btn btn--ghost" id="btnFiltrarCfop">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Código</th><th>Descrição</th><th>Tipo</th></tr></thead>
      <tbody id="tblCfopBody"><tr><td colspan="3" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnFiltrarCfop")!.addEventListener("click", () => void carregarCfop());
  await carregarCfop();
}

async function carregarCfop(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblCfopBody");
  if (!$body) return;
  const tipo = (currentApp?.querySelector<HTMLSelectElement>("#filtroCfopTipo")?.value || "").trim() || undefined;
  try {
    const res = await api.listarCfop(tipo);
    if (!res.length) { $body.innerHTML = `<tr><td colspan="3" class="pdv-sem-res">Nenhum CFOP</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr><td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(c.codigo)}</td><td>${escapeHtml(c.descricao)}</td><td><span class="badge badge--muted">${c.tipo}</span></td></tr>`).join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="3" class="pdv-sem-res">Erro</td></tr>`;
  }
}

// ──────────────────────────────────────────────────────────
//  CST
// ──────────────────────────────────────────────────────────

async function renderCst($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <div class="estq-filtros">
      <div class="field"><label>Tabela</label>
        <select id="filtroCstTab"><option value="cst_icms">ICMS</option><option value="cst_pis">PIS</option><option value="cst_cofins">COFINS</option></select>
      </div>
      <button class="btn btn--ghost" id="btnFiltrarCst">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Código</th><th>Descrição</th></tr></thead>
      <tbody id="tblCstBody"><tr><td colspan="2" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnFiltrarCst")!.addEventListener("click", () => void carregarCst());
  await carregarCst();
}

async function carregarCst(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblCstBody");
  if (!$body) return;
  const tab = currentApp?.querySelector<HTMLSelectElement>("#filtroCstTab")?.value || "cst_icms";
  try {
    const res = await api.listarCst(tab);
    if (!res.length) { $body.innerHTML = `<tr><td colspan="2" class="pdv-sem-res">Nenhum CST</td></tr>`; return; }
    $body.innerHTML = res.map((c: CstCode) => `
      <tr><td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(c.codigo)}</td><td>${escapeHtml(c.descricao)}</td></tr>`).join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="2" class="pdv-sem-res">Erro</td></tr>`;
  }
}

// ──────────────────────────────────────────────────────────
//  Config Fiscal
// ──────────────────────────────────────────────────────────

async function renderConfig($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnGerarConfig">Gerar config padrão</button></p>
    <div class="estq-filtros">
      <div class="field"><label>Busca</label><input id="filtroConfQ" placeholder="Produto, SKU, NCM…" autocomplete="off"></div>
      <button class="btn btn--ghost" id="btnFiltrarConf">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Produto</th><th>NCM</th><th>CFOP</th><th>CST ICMS</th><th>PIS</th><th>COFINS</th><th>ICMS%</th><th></th></tr></thead>
      <tbody id="tblConfBody"><tr><td colspan="8" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnGerarConfig")!.addEventListener("click", async () => {
    try {
      const r = await api.gerarFiscalConfig();
      toast(`${r.gerados} configurações geradas`, "success");
      await carregarConfig();
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  });
  $ct.querySelector<HTMLElement>("#btnFiltrarConf")!.addEventListener("click", () => void carregarConfig());
  $ct.querySelector<HTMLInputElement>("#filtroConfQ")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") void carregarConfig();
  });
  await carregarConfig();
}

async function carregarConfig(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblConfBody");
  if (!$body) return;
  const q = (currentApp?.querySelector<HTMLInputElement>("#filtroConfQ")?.value || "").trim() || undefined;
  try {
    const res = await api.listarFiscalConfig({ q, limit: 200 });
    if (!res.length) { $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Nenhuma config</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr>
        <td><strong>${escapeHtml(c.produto_nome)}</strong>${c.sku ? `<div style="font-size:11px;color:var(--ink-faint);font-family:var(--font-mono);">${escapeHtml(c.sku)}</div>` : ""}</td>
        <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(c.ncm || "—")}</td>
        <td style="font-family:var(--font-mono);font-size:12px;">${c.cfop ? escapeHtml(c.cfop) : "—"}</td>
        <td style="font-size:12px;">${c.cst_icms ? escapeHtml(c.cst_icms) : "—"}</td>
        <td style="font-size:12px;">${c.cst_pis ? escapeHtml(c.cst_pis) : "—"}</td>
        <td style="font-size:12px;">${c.cst_cofins ? escapeHtml(c.cst_cofins) : "—"}</td>
        <td>${c.aliquota_icms ? c.aliquota_icms + "%" : "—"}</td>
        <td class="cell-actions"><button class="btn btn--ghost btn--sm" data-editar="${c.variante_id}">Editar</button></td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-editar]").forEach((b) => {
      b.addEventListener("click", () => {
        const c = res.find((x) => x.variante_id === Number(b.dataset.editar));
        if (c) abrirModalFiscal(c);
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalFiscal(c: FiscalConfigItem): void {
  openModal(
    `<div class="modal-head"><h3>Config Fiscal — ${escapeHtml(c.produto_nome)}</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>NCM</label><input id="fiNcm" value="${escapeHtml(c.ncm || "")}" autocomplete="off" maxlength="8"></div>
       <div class="field"><label>CFOP</label><input id="fiCfop" value="${c.cfop || ""}" autocomplete="off" maxlength="4"></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>CST ICMS</label><input id="fiCstIcms" value="${c.cst_icms || ""}" maxlength="2"></div>
         <div class="field" style="flex:1"><label>Alíq. ICMS %</label><input id="fiIcms" type="number" step="0.01" value="${c.aliquota_icms || 0}"></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>CST PIS</label><input id="fiCstPis" value="${c.cst_pis || ""}" maxlength="2"></div>
         <div class="field" style="flex:1"><label>Alíq. PIS %</label><input id="fiPis" type="number" step="0.01" value="${c.aliquota_pis || 0}"></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>CST COFINS</label><input id="fiCstCofins" value="${c.cst_cofins || ""}" maxlength="2"></div>
         <div class="field" style="flex:1"><label>Alíq. COFINS %</label><input id="fiCofins" type="number" step="0.01" value="${c.aliquota_cofins || 0}"></div>
       </div>
       <div class="field"><label>Alíq. IPI %</label><input id="fiIpi" type="number" step="0.01" value="${c.aliquota_ipi || 0}"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="fiSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#fiSalvar")!.onclick = async () => {
          try {
            await api.upsertFiscalConfig(c.variante_id, {
              ncm: (m.querySelector<HTMLInputElement>("#fiNcm")?.value || "").trim() || undefined,
              cfop: (m.querySelector<HTMLInputElement>("#fiCfop")?.value || "").trim() || undefined,
              cst_icms: (m.querySelector<HTMLInputElement>("#fiCstIcms")?.value || "").trim() || undefined,
              cst_pis: (m.querySelector<HTMLInputElement>("#fiCstPis")?.value || "").trim() || undefined,
              cst_cofins: (m.querySelector<HTMLInputElement>("#fiCstCofins")?.value || "").trim() || undefined,
              aliquota_icms: parseFloat((m.querySelector<HTMLInputElement>("#fiIcms")?.value || "0").replace(",", ".")),
              aliquota_pis: parseFloat((m.querySelector<HTMLInputElement>("#fiPis")?.value || "0").replace(",", ".")),
              aliquota_cofins: parseFloat((m.querySelector<HTMLInputElement>("#fiCofins")?.value || "0").replace(",", ".")),
              aliquota_ipi: parseFloat((m.querySelector<HTMLInputElement>("#fiIpi")?.value || "0").replace(",", ".")),
            });
            toast("Config salva", "success");
            closeModal();
            await carregarConfig();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ─── Emitente ──────────────────────────────────────────────

async function renderEmitente($ct: HTMLElement): Promise<void> {
  let e: Record<string, unknown> = {};
  try { e = await api.getEmitente() as unknown as Record<string, unknown>; } catch { }
  $ct.innerHTML = `<div class="field-row" style="flex-direction:column;gap:10px;max-width:600px;">
    <div class="field"><label>Razão Social</label><input id="emRazao" value="${escapeHtml(String(e.razao_social || ""))}"></div>
    <div class="field"><label>CNPJ</label><input id="emCnpj" value="${escapeHtml(String(e.cnpj || ""))}"></div>
    <div class="field"><label>IE</label><input id="emIe" value="${escapeHtml(String(e.ie || ""))}"></div>
    <div class="field"><label>Regime Tributário</label>
      <select id="emRegime"><option value="simples_nacional" ${e.regime_tributario === "simples_nacional" ? "selected" : ""}>Simples Nacional</option>
      <option value="lucro_presumido" ${e.regime_tributario === "lucro_presumido" ? "selected" : ""}>Lucro Presumido</option>
      <option value="lucro_real" ${e.regime_tributario === "lucro_real" ? "selected" : ""}>Lucro Real</option></select></div>
    <div class="field"><label>Token Focus NFe</label><input id="emToken" type="password" value="${escapeHtml(String(e.token_focus || ""))}"></div>
    <div class="field"><label>Alíq. ICMS %</label><input id="emIcms" type="number" step="0.01" value="${e.aliquota_icms || 18}"></div>
    <button class="btn btn--accent" id="emSalvar">Salvar emitente</button></div>`;
  $ct.querySelector<HTMLElement>("#emSalvar")!.onclick = async () => {
    try {
      await api.upsertEmitente({
        razao_social: ($ct.querySelector<HTMLInputElement>("#emRazao")?.value || "").trim(),
        cnpj: ($ct.querySelector<HTMLInputElement>("#emCnpj")?.value || "").trim(),
        ie: ($ct.querySelector<HTMLInputElement>("#emIe")?.value || "").trim(),
        regime_tributario: $ct.querySelector<HTMLSelectElement>("#emRegime")?.value || "simples_nacional",
        token_focus: ($ct.querySelector<HTMLInputElement>("#emToken")?.value || "").trim(),
        aliquota_icms: parseFloat($ct.querySelector<HTMLInputElement>("#emIcms")?.value || "0"),
      });
      toast("Emitente salvo", "success");
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };
}

// ─── NF-e ──────────────────────────────────────────────────

async function renderNfe($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `<div class="tab-bar"><button class="tab-btn is-active" data-subaba="saida">Saída</button>
    <button class="tab-btn" data-subaba="entrada">Entrada</button></div><div id="nfeContent"><p class="pdv-sem-res">Carregando…</p></div>`;
  let sub = "saida";
  const load = async () => {
    const $n = $ct.querySelector<HTMLElement>("#nfeContent")!;
    try {
      if (sub === "saida") {
        const r = await api.listarNfeSaida();
        $n.innerHTML = !r.length ? `<p class="pdv-sem-res">Nenhuma NF-e de saída</p>` :
          `<div class="table-wrap"><table class="data-table"><thead><tr><th>Nº</th><th>Cliente</th><th>Valor</th><th>Status</th><th>Data</th></tr></thead>
          <tbody>${r.map((n) => `<tr><td style="font-family:var(--font-mono);">${n.numero}</td><td>${escapeHtml(n.cliente_nome)}</td><td>${fmtMoney(n.valor)}</td>
          <td><span class="badge badge--${n.status === "autorizada" ? "ok" : "muted"}">${n.status}</span></td><td style="font-size:12px;">${fmtDate(n.criado_em)}</td></tr>`).join("")}</tbody></table></div>`;
      } else {
        const r = await api.listarNfeEntrada();
        $n.innerHTML = !r.length ? `<p class="pdv-sem-res">Nenhuma NF-e de entrada</p>` :
          `<div class="table-wrap"><table class="data-table"><thead><tr><th>Chave</th><th>Fornecedor</th><th>Valor</th><th>Emissão</th></tr></thead>
          <tbody>${r.map((n) => `<tr><td style="font-family:var(--font-mono);font-size:11px;">${escapeHtml(n.chave)}</td><td>${escapeHtml(n.fornecedor_nome)}</td><td>${fmtMoney(n.valor)}</td><td style="font-size:12px;">${fmtDate(n.data_emissao)}</td></tr>`).join("")}</tbody></table></div>`;
      }
    } catch { $n.innerHTML = `<p class="pdv-sem-res">Erro</p>`; }
  };
  $ct.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => { sub = btn.dataset.subaba || "saida"; $ct.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("is-active")); btn.classList.add("is-active"); void load(); });
  });
  void load();
}

// ─── IBPT ──────────────────────────────────────────────────

async function renderIbpt($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `<div class="estq-filtros"><div class="field"><label>NCM</label><input id="ibptNcm" placeholder="Buscar NCM…"></div>
    <button class="btn btn--ghost" id="btnFiltrarIbpt">Filtrar</button></div>
    <div class="table-wrap"><table class="data-table"><thead><tr><th>NCM</th><th>Federal%</th><th>Estadual%</th><th>Municipal%</th></tr></thead>
    <tbody id="tblIbptBody"><tr><td colspan="4" class="pdv-sem-res">Carregando…</td></tr></tbody></table></div>`;
  const $body = $ct.querySelector<HTMLElement>("#tblIbptBody")!;
  const load = async () => {
    try {
      const r = await api.listarIbpt({ ncm: ($ct.querySelector<HTMLInputElement>("#ibptNcm")?.value || "").trim() || undefined, limit: 50 });
      if (!r.length) { $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Nenhum</td></tr>`; return; }
      $body.innerHTML = r.map((i) => `<tr><td style="font-family:var(--font-mono);">${escapeHtml(i.ncm)}</td><td>${i.aliquota_federal}%</td><td>${i.aliquota_estadual}%</td><td>${i.aliquota_municipal}%</td></tr>`).join("");
    } catch { $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Erro</td></tr>`; }
  };
  $ct.querySelector<HTMLElement>("#btnFiltrarIbpt")!.addEventListener("click", () => void load());
  $ct.querySelector<HTMLInputElement>("#ibptNcm")?.addEventListener("keydown", (e) => { if (e.key === "Enter") void load(); });
  void load();
}
