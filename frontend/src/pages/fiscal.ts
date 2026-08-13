import "../styles/estoque.css";
import { api, type BeneficioFiscalItem, type CestItem, type CsosnItem, type CstCode, type FiscalConfigItem, type FiscalResultado, type ProdutoResumo } from "../api/client";
import { escapeHtml, fmtDate, fmtDateTime, fmtMoney } from "../ui/format";
import { closeModal, confirmDialog, openModal, toast } from "../ui/dom";

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
      <button class="tab-btn ${abaAtiva === "cest" ? "is-active" : ""}" data-aba="cest">CEST</button>
      <button class="tab-btn ${abaAtiva === "config" ? "is-active" : ""}" data-aba="config">Config. Fiscal</button>
      <button class="tab-btn ${abaAtiva === "emitente" ? "is-active" : ""}" data-aba="emitente">Emitente</button>
      <button class="tab-btn ${abaAtiva === "nfe" ? "is-active" : ""}" data-aba="nfe">NF-e</button>
      <button class="tab-btn ${abaAtiva === "ibpt" ? "is-active" : ""}" data-aba="ibpt">IBPT</button>
      <button class="tab-btn ${abaAtiva === "sugestoes" ? "is-active" : ""}" data-aba="sugestoes">Sugestões NCM</button>
      <button class="tab-btn ${abaAtiva === "simulador" ? "is-active" : ""}" data-aba="simulador">Simulador</button>
      <button class="tab-btn ${abaAtiva === "historico" ? "is-active" : ""}" data-aba="historico">Histórico</button>
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
  else if (abaAtiva === "cest") await renderCest($ct);
  else if (abaAtiva === "config") await renderConfig($ct);
  else if (abaAtiva === "emitente") await renderEmitente($ct);
  else if (abaAtiva === "nfe") await renderNfe($ct);
  else if (abaAtiva === "ibpt") await renderIbpt($ct);
  else if (abaAtiva === "sugestoes") await renderSugestoes($ct);
  else if (abaAtiva === "simulador") renderSimulador($ct);
  else if (abaAtiva === "historico") await renderHistoricoFiscal($ct);
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
//  CEST
// ──────────────────────────────────────────────────────────

async function renderCest($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <div class="estq-filtros">
      <div class="field"><label>NCM</label><input id="filtroCestNcm" placeholder="Ex.: 8544" autocomplete="off"></div>
      <button class="btn btn--ghost" id="btnFiltrarCest">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>CEST</th><th>NCM</th><th>Descrição</th><th>Vigência</th></tr></thead>
      <tbody id="tblCestBody"><tr><td colspan="4" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnFiltrarCest")!.addEventListener("click", () => void carregarCest());
  $ct.querySelector<HTMLInputElement>("#filtroCestNcm")?.addEventListener("keydown", (e) => { if (e.key === "Enter") void carregarCest(); });
  await carregarCest();
}

async function carregarCest(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblCestBody");
  if (!$body) return;
  const ncm = (currentApp?.querySelector<HTMLInputElement>("#filtroCestNcm")?.value || "").trim() || undefined;
  try {
    const res = await api.listarCest(ncm);
    if (!res.length) { $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Nenhum CEST</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr>
        <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(c.codigo)}</td>
        <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(c.ncm_prefix || "—")}</td>
        <td>${escapeHtml(c.descricao || "—")}</td>
        <td style="font-size:12px;">${c.vigencia_inicio ? fmtDate(c.vigencia_inicio) : ""}${c.vigencia_fim ? " → " + fmtDate(c.vigencia_fim) : ""}</td>
      </tr>`).join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Erro</td></tr>`;
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
        if (c) void abrirModalFiscal(c);
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Erro</td></tr>`;
  }
}

const ORIGENS = [
  "Nacional (exceto 3 a 5 e 7 a 8)",
  "Estrangeira — importação direta",
  "Estrangeira — adquirida no mercado interno",
  "Nacional, conteúdo importação > 40%",
  "Nacional, produção conforme processo produtivo básico",
  "Nacional, conteúdo importação ≤ 40%",
  "Estrangeira — importação direta, sem similar nacional",
  "Estrangeira — mercado interno, sem similar nacional",
  "Nacional, conteúdo importação > 70%",
];

async function abrirModalFiscal(c: FiscalConfigItem): Promise<void> {
  let cests: CestItem[] = [];
  let csosns: CsosnItem[] = [];
  let benefs: BeneficioFiscalItem[] = [];
  try {
    const [a, b, d] = await Promise.all([
      api.listarCest(c.ncm || undefined),
      api.listarCsosn(),
      api.listarBeneficiosFiscais(),
    ]);
    cests = a;
    csosns = b;
    benefs = d;
  } catch { /* sem opções de lookup */ }
  const sel = (opts: { v: string; t: string }[], atual: string) =>
    `<option value="">—</option>` +
    opts.map((o) => `<option value="${escapeHtml(o.v)}" ${o.v === atual ? "selected" : ""}>${escapeHtml(o.t)}</option>`).join("");
  const cestOpts = sel(cests.map((x) => ({ v: x.codigo, t: `${x.codigo} · ${x.descricao || ""}`.trim() })), c.cest || "");
  const csosnOpts = sel(csosns.map((x) => ({ v: x.codigo, t: `${x.codigo} · ${x.descricao}` })), c.csosn || "");
  const benefOpts =
    `<option value="">Nenhum</option>` +
    benefs.map((x) => `<option value="${x.id}" ${String(x.id) === String(c.beneficio_id ?? "") ? "selected" : ""}>${escapeHtml(x.descricao)}</option>`).join("");
  const origemOpts = ORIGENS.map((t, i) => `<option value="${i}" ${(c.origem ?? 0) === i ? "selected" : ""}>${i} · ${t}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>Config Fiscal — ${escapeHtml(c.produto_nome)}</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field-row">
         <div class="field" style="flex:1"><label>NCM</label><input id="fiNcm" value="${escapeHtml(c.ncm || "")}" autocomplete="off" maxlength="8"></div>
         <div class="field" style="flex:1"><label>CFOP</label><input id="fiCfop" value="${c.cfop || ""}" autocomplete="off" maxlength="4"></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Origem</label><select id="fiOrigem">${origemOpts}</select></div>
         <div class="field" style="flex:1"><label>CEST</label><select id="fiCest">${cestOpts}</select></div>
         <div class="field" style="flex:1"><label>CSOSN (Simples)</label><select id="fiCsosn">${csosnOpts}</select></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>CST ICMS</label><input id="fiCstIcms" value="${c.cst_icms || ""}" maxlength="2"></div>
         <div class="field" style="flex:1"><label>Alíq. ICMS %</label><input id="fiIcms" type="number" step="0.01" value="${c.aliquota_icms || 0}"></div>
         <div class="field" style="flex:1"><label>Alíq. ICMS-ST %</label><input id="fiIcmsSt" type="number" step="0.01" value="${c.aliquota_icms_st || 0}"></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>MVA %</label><input id="fiMva" type="number" step="0.01" value="${c.mva || 0}"></div>
         <div class="field" style="flex:1"><label>Redução base %</label><input id="fiBaseRed" type="number" step="0.01" value="${c.base_reducao || 0}"></div>
         <div class="field" style="flex:1"><label>Alíq. Interestadual %</label><input id="fiInter" type="number" step="0.01" value="${c.aliquota_interestadual || 0}"></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>FECP %</label><input id="fiFecp" type="number" step="0.01" value="${c.aliquota_fecp || 0}"></div>
         <div class="field" style="flex:1"><label>Crédito ICMS %</label><input id="fiCred" type="number" step="0.01" value="${c.credito_icms || 0}"></div>
         <div class="field" style="flex:1"><label>Benefício fiscal</label><select id="fiBenef">${benefOpts}</select></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>CST PIS</label><input id="fiCstPis" value="${c.cst_pis || ""}" maxlength="2"></div>
         <div class="field" style="flex:1"><label>Alíq. PIS %</label><input id="fiPis" type="number" step="0.01" value="${c.aliquota_pis || 0}"></div>
         <div class="field" style="flex:1"><label>CST COFINS</label><input id="fiCstCofins" value="${c.cst_cofins || ""}" maxlength="2"></div>
         <div class="field" style="flex:1"><label>Alíq. COFINS %</label><input id="fiCofins" type="number" step="0.01" value="${c.aliquota_cofins || 0}"></div>
       </div>
       <div class="field"><label>Alíq. IPI %</label><input id="fiIpi" type="number" step="0.01" value="${c.aliquota_ipi || 0}"></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Vigência início</label><input id="fiVigIni" type="date" value="${c.vigencia_inicio || ""}"></div>
         <div class="field" style="flex:1"><label>Vigência fim</label><input id="fiVigFim" type="date" value="${c.vigencia_fim || ""}"></div>
       </div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="fiSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#fiSalvar")!.onclick = async () => {
          const num = (id: string) => {
            const v = (m.querySelector<HTMLInputElement>(id)?.value || "").replace(",", ".");
            return v === "" ? undefined : parseFloat(v);
          };
          const benef = m.querySelector<HTMLSelectElement>("#fiBenef")?.value || "";
          try {
            await api.upsertFiscalConfig(c.variante_id, {
              ncm: (m.querySelector<HTMLInputElement>("#fiNcm")?.value || "").trim() || undefined,
              cfop: (m.querySelector<HTMLInputElement>("#fiCfop")?.value || "").trim() || undefined,
              origem: parseInt(m.querySelector<HTMLSelectElement>("#fiOrigem")?.value || "0", 10),
              cest: (m.querySelector<HTMLSelectElement>("#fiCest")?.value || "") || undefined,
              csosn: (m.querySelector<HTMLSelectElement>("#fiCsosn")?.value || "") || undefined,
              cst_icms: (m.querySelector<HTMLInputElement>("#fiCstIcms")?.value || "").trim() || undefined,
              aliquota_icms: num("#fiIcms"),
              aliquota_icms_st: num("#fiIcmsSt"),
              mva: num("#fiMva"),
              base_reducao: num("#fiBaseRed"),
              aliquota_interestadual: num("#fiInter"),
              aliquota_fecp: num("#fiFecp"),
              credito_icms: num("#fiCred"),
              beneficio_id: benef ? parseInt(benef, 10) : null,
              cst_pis: (m.querySelector<HTMLInputElement>("#fiCstPis")?.value || "").trim() || undefined,
              aliquota_pis: num("#fiPis"),
              cst_cofins: (m.querySelector<HTMLInputElement>("#fiCstCofins")?.value || "").trim() || undefined,
              aliquota_cofins: num("#fiCofins"),
              aliquota_ipi: num("#fiIpi"),
              vigencia_inicio: (m.querySelector<HTMLInputElement>("#fiVigIni")?.value || "") || null,
              vigencia_fim: (m.querySelector<HTMLInputElement>("#fiVigFim")?.value || "") || null,
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
    <div class="field"><label>CRT</label>
      <select id="emCrt"><option value="1" ${String(e.crt ?? 1) === "1" ? "selected" : ""}>1 — Simples Nacional</option>
      <option value="2" ${String(e.crt ?? 1) === "2" ? "selected" : ""}>2 — Simples (excesso de sublimite)</option>
      <option value="3" ${String(e.crt ?? 1) === "3" ? "selected" : ""}>3 — Regime Normal</option></select></div>
    <div class="field"><label>Token Focus NFe</label><input id="emToken" type="password" value="${escapeHtml(String(e.token_focus || ""))}"></div>
    <div class="field"><label>Alíq. ICMS %</label><input id="emIcms" type="number" step="0.01" value="${e.aliquota_icms || 18}"></div>
    <div class="field-row">
      <div class="field" style="flex:1"><label>Alíq. IBS % (transição — validar)</label><input id="emIbs" type="number" step="0.01" value="${e.aliquota_ibs || 0}"></div>
      <div class="field" style="flex:1"><label>Alíq. CBS % (transição — validar)</label><input id="emCbs" type="number" step="0.01" value="${e.aliquota_cbs || 0}"></div>
    </div>
    <div class="field-row">
      <div class="field" style="flex:1"><label>Vigência IBS início</label><input id="emIbsIni" type="date" value="${e.ibs_vigencia_inicio || ""}"></div>
      <div class="field" style="flex:1"><label>Vigência IBS fim</label><input id="emIbsFim" type="date" value="${e.ibs_vigencia_fim || ""}"></div>
    </div>
    <div class="field-row">
      <div class="field" style="flex:1"><label>Vigência CBS início</label><input id="emCbsIni" type="date" value="${e.cbs_vigencia_inicio || ""}"></div>
      <div class="field" style="flex:1"><label>Vigência CBS fim</label><input id="emCbsFim" type="date" value="${e.cbs_vigencia_fim || ""}"></div>
    </div>
    <button class="btn btn--accent" id="emSalvar">Salvar emitente</button></div>`;
  $ct.querySelector<HTMLElement>("#emSalvar")!.onclick = async () => {
    try {
      await api.upsertEmitente({
        razao_social: ($ct.querySelector<HTMLInputElement>("#emRazao")?.value || "").trim(),
        cnpj: ($ct.querySelector<HTMLInputElement>("#emCnpj")?.value || "").trim(),
        ie: ($ct.querySelector<HTMLInputElement>("#emIe")?.value || "").trim(),
        regime_tributario: $ct.querySelector<HTMLSelectElement>("#emRegime")?.value || "simples_nacional",
        crt: parseInt($ct.querySelector<HTMLSelectElement>("#emCrt")?.value || "1", 10) || 1,
        token_focus: ($ct.querySelector<HTMLInputElement>("#emToken")?.value || "").trim(),
        aliquota_icms: parseFloat($ct.querySelector<HTMLInputElement>("#emIcms")?.value || "0"),
        aliquota_ibs: parseFloat($ct.querySelector<HTMLInputElement>("#emIbs")?.value || "0"),
        aliquota_cbs: parseFloat($ct.querySelector<HTMLInputElement>("#emCbs")?.value || "0"),
        ibs_vigencia_inicio: $ct.querySelector<HTMLInputElement>("#emIbsIni")?.value || null,
        ibs_vigencia_fim: $ct.querySelector<HTMLInputElement>("#emIbsFim")?.value || null,
        cbs_vigencia_inicio: $ct.querySelector<HTMLInputElement>("#emCbsIni")?.value || null,
        cbs_vigencia_fim: $ct.querySelector<HTMLInputElement>("#emCbsFim")?.value || null,
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

// ─── Histórico (auditoria) ────────────────────────────────

async function renderHistoricoFiscal($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <div class="estq-filtros">
      <div class="field"><label>Busca</label><input id="fhQ" placeholder="Produto, SKU, NCM…" autocomplete="off"></div>
      <button class="btn btn--ghost" id="fhFiltrar">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Data</th><th>Produto</th><th>Tipo</th><th>NCM</th><th>CEST</th><th>CSOSN</th><th>ICMS%</th><th>ST%</th><th>MVA%</th><th>Por</th></tr></thead>
      <tbody id="tblFhBody"><tr><td colspan="10" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  const carregar = async () => {
    const $body = currentApp?.querySelector<HTMLElement>("#tblFhBody");
    if (!$body) return;
    const q = (currentApp?.querySelector<HTMLInputElement>("#fhQ")?.value || "").trim() || undefined;
    try {
      const res = await api.listarHistoricoFiscal({ q });
      if (!res.length) { $body.innerHTML = `<tr><td colspan="10" class="pdv-sem-res">Nenhum registro</td></tr>`; return; }
      $body.innerHTML = res.map((h) => `
        <tr>
          <td style="font-size:12px;color:var(--ink-soft);">${fmtDateTime(h.criado_em)}</td>
          <td><strong>${escapeHtml(h.produto_nome)}</strong>${h.sku ? `<div style="font-size:11px;color:var(--ink-faint);font-family:var(--font-mono);">${escapeHtml(h.sku)}</div>` : ""}</td>
          <td><span class="badge badge--${h.tipo === "criado" ? "muted" : "ok"}">${h.tipo}</span></td>
          <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(h.ncm || "—")}</td>
          <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(h.cest || "—")}</td>
          <td style="font-size:12px;">${escapeHtml(h.csosn || "—")}</td>
          <td>${h.aliquota_icms ? h.aliquota_icms + "%" : "—"}</td>
          <td>${h.aliquota_icms_st ? h.aliquota_icms_st + "%" : "—"}</td>
          <td>${h.mva ? h.mva + "%" : "—"}</td>
          <td>${h.usuario_nome ? escapeHtml(h.usuario_nome) : "—"}</td>
        </tr>`).join("");
    } catch {
      $body.innerHTML = `<tr><td colspan="10" class="pdv-sem-res">Erro</td></tr>`;
    }
  };
  $ct.querySelector<HTMLElement>("#fhFiltrar")!.addEventListener("click", () => void carregar());
  $ct.querySelector<HTMLInputElement>("#fhQ")?.addEventListener("keydown", (e) => { if (e.key === "Enter") void carregar(); });
  await carregar();
}

// ─── Simulador fiscal ──────────────────────────────────────

let simVariante: ProdutoResumo | null = null;

function renderSimulador($ct: HTMLElement): void {
  simVariante = null;
  $ct.innerHTML = `
    <div class="estq-filtros" style="align-items:flex-end;flex-wrap:wrap;">
      <div class="field" style="min-width:260px;"><label>Produto / variante</label>
        <input id="fsBusca" placeholder="Nome, SKU…" autocomplete="off"></div>
      <div class="field" style="min-width:200px;"><label>Cliente (opcional)</label>
        <input id="fsCli" placeholder="Nome, CPF…" autocomplete="off"></div>
      <div class="field"><label>UF destino</label><input id="fsUf" maxlength="2" style="width:70px;"></div>
      <div class="field"><label>Tipo cliente</label>
        <select id="fsTipoCliente"><option value="">—</option><option value="PF">PF</option><option value="PJ">PJ</option></select></div>
      <div class="field"><label>Contribuinte</label>
        <select id="fsContribuinte"><option value="">—</option><option value="contribuinte">Contribuinte</option><option value="nao_contribuinte">Não contribuinte</option></select></div>
      <div class="field"><label>Modelo</label>
        <select id="fsModelo"><option value="">—</option><option value="55">NF-e 55</option><option value="65">NFC-e 65</option></select></div>
      <div class="field"><label>Operação</label>
        <select id="fsOperacao"><option value="venda">Venda</option><option value="compra">Compra</option></select></div>
      <div class="field"><label>Data</label><input id="fsData" type="date" value="${new Date().toISOString().slice(0, 10)}"></div>
      <div class="field"><label>Qtd</label><input id="fsQtd" type="number" min="0" step="any" value="1" style="width:70px;"></div>
      <div class="field"><label>Valor unit.</label><input id="fsValor" type="number" min="0" step="0.01" value="100" style="width:90px;"></div>
      <div class="field"><label>Desconto</label><input id="fsDesc" type="number" min="0" step="0.01" value="0" style="width:80px;"></div>
      <button class="btn btn--accent" id="fsSimular">Simular</button>
    </div>
    <div id="fsSugProd"></div>
    <div id="fsSugCli"></div>
    <div id="fsSel"></div>
    <div id="fsResult"></div>
  `;
  let timerP: ReturnType<typeof setTimeout> | undefined;
  const $busca = $ct.querySelector<HTMLInputElement>("#fsBusca")!;
  $busca.addEventListener("input", () => {
    clearTimeout(timerP);
    timerP = setTimeout(() => void fsBuscarProd($busca.value.trim()), 200);
  });
  let timerC: ReturnType<typeof setTimeout> | undefined;
  const $cli = $ct.querySelector<HTMLInputElement>("#fsCli")!;
  $cli.addEventListener("input", () => {
    clearTimeout(timerC);
    timerC = setTimeout(() => void fsBuscarCli($cli.value.trim()), 200);
  });
  $ct.querySelector<HTMLElement>("#fsSimular")!.addEventListener("click", () => void fsSimular($ct));
}

async function fsBuscarProd(q: string): Promise<void> {
  const $sug = currentApp?.querySelector<HTMLElement>("#fsSugProd");
  if (!$sug) return;
  if (!q) { $sug.innerHTML = ""; return; }
  try {
    const res = await api.listarProdutos({ q, limit: 8, agrupado: 0 });
    const items = res.items.filter((i): i is ProdutoResumo => "price" in i);
    if (!items.length) { $sug.innerHTML = `<p class="pdv-sem-res">Nenhum</p>`; return; }
    $sug.innerHTML = items.map((p, i) => `
      <button type="button" class="sim-sug-item" data-sim="${i}">
        <span><b>${escapeHtml(p.name)}</b>${p.sku ? ` <span style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">${escapeHtml(p.sku)}</span>` : ""}</span>
      </button>`).join("");
    $sug.querySelectorAll<HTMLElement>("[data-sim]").forEach((b) => {
      b.addEventListener("click", () => {
        simVariante = items[Number(b.dataset.sim)];
        $sug.innerHTML = "";
        const $sel = currentApp?.querySelector<HTMLElement>("#fsSel");
        if ($sel) $sel.innerHTML = `<p class="sim-sel">Produto: <b>${escapeHtml(simVariante.name)}</b>${simVariante.sku ? ` <span style="font-family:var(--font-mono);font-size:11px;">${escapeHtml(simVariante.sku)}</span>` : ""}</p>`;
      });
    });
  } catch { $sug.innerHTML = `<p class="pdv-sem-res">Erro</p>`; }
}

async function fsBuscarCli(q: string): Promise<void> {
  const $sug = currentApp?.querySelector<HTMLElement>("#fsSugCli");
  if (!$sug) return;
  if (!q) { $sug.innerHTML = ""; return; }
  try {
    const res = await api.buscarClientes(q);
    if (!res.length) { $sug.innerHTML = `<p class="pdv-sem-res">Nenhum cliente</p>`; return; }
    $sug.innerHTML = res.map((c, i) => `
      <button type="button" class="sim-sug-item" data-cli="${i}">
        <span><b>${escapeHtml(c.nome)}</b>${c.doc ? ` <span style="font-family:var(--font-mono);font-size:11px;">${escapeHtml(c.doc)}</span>` : ""}</span>
      </button>`).join("");
    $sug.querySelectorAll<HTMLElement>("[data-cli]").forEach((b) => {
      b.addEventListener("click", () => {
        const cli = res[Number(b.dataset.cli)];
        $sug.innerHTML = "";
        const $sel = currentApp?.querySelector<HTMLElement>("#fsSel");
        if ($sel) $sel.insertAdjacentHTML("beforeend", `<p class="sim-sel">Cliente: <b>${escapeHtml(cli.nome)}</b></p>`);
        const $cli = currentApp?.querySelector<HTMLInputElement>("#fsCli");
        if ($cli) $cli.dataset.cliId = String(cli.id);
      });
    });
  } catch { $sug.innerHTML = `<p class="pdv-sem-res">Erro</p>`; }
}

async function fsSimular($ct: HTMLElement): Promise<void> {
  const $result = $ct.querySelector<HTMLElement>("#fsResult")!;
  if (!simVariante) { toast("Selecione um produto", "error"); return; }
  const $cli = $ct.querySelector<HTMLInputElement>("#fsCli")!;
  const payload: Record<string, unknown> = {
    variante_id: simVariante.id,
    operacao: $ct.querySelector<HTMLSelectElement>("#fsOperacao")?.value || "venda",
    data: $ct.querySelector<HTMLInputElement>("#fsData")?.value || undefined,
    quantidade: parseFloat($ct.querySelector<HTMLInputElement>("#fsQtd")?.value || "1"),
    valor_unitario: parseFloat($ct.querySelector<HTMLInputElement>("#fsValor")?.value || "0"),
    desconto: parseFloat($ct.querySelector<HTMLInputElement>("#fsDesc")?.value || "0"),
    uf_destino: ($ct.querySelector<HTMLInputElement>("#fsUf")?.value || "").trim().toUpperCase() || undefined,
    tipo_cliente: $ct.querySelector<HTMLSelectElement>("#fsTipoCliente")?.value || undefined,
    contribuinte: $ct.querySelector<HTMLSelectElement>("#fsContribuinte")?.value || undefined,
    modelo_documento: $ct.querySelector<HTMLSelectElement>("#fsModelo")?.value || undefined,
  };
  const cliId = $cli?.dataset.cliId;
  if (cliId) payload.cliente_id = parseInt(cliId, 10);
  $result.innerHTML = `<p class="pdv-sem-res">Calculando…</p>`;
  try {
    const sim = await api.simularFiscal(payload);
    $result.innerHTML = fsResultHtml(sim.resultado);
  } catch (e) {
    $result.innerHTML = `<p class="pdv-sem-res">Erro: ${escapeHtml((e as Error).message)}</p>`;
  }
}

function fsResultHtml(r: FiscalResultado): string {
  const linha = (rot: string, val: string) => `<tr><td class="rot">${rot}</td><td class="num">${val}</td></tr>`;
  const valCls = r.status_validacao === "erro" ? "badge badge--cancelada" : "badge badge--ok";
  const probs = (r.problemas || []).map((p) => `
    <li class="${p.tipo === "ERROR" ? "sim-prob-err" : p.tipo === "WARNING" ? "sim-prob-warn" : "sim-prob-info"}">
      <b>${p.tipo}</b> · ${escapeHtml(p.campo)} — ${escapeHtml(p.mensagem)}
    </li>`).join("");
  const dec = (r.decisao || []).map((d) => `<li><b>${escapeHtml(d.passo)}</b>: ${escapeHtml(d.detalhe)}</li>`).join("");
  return `
    <div class="sim-card">
      <h3 style="margin:0 0 10px;">Simulação — ${r.cfop || "—"} <span class="${valCls}">${r.status_validacao === "erro" ? "ERROR (bloqueado)" : "ok"}</span></h3>
      <div class="table-wrap" style="max-width:480px;">
        <table class="data-table"><tbody>
          ${linha("NCM / CEST", `${escapeHtml(r.ncm || "—")}${r.cest ? " · " + escapeHtml(r.cest) : ""}`)}
          ${linha("CFOP", r.cfop || "—")}
          ${linha("CST / CSOSN", `${escapeHtml(r.cst_icms || r.csosn || "—")}${r.cst_ibs || r.cst_cbs ? ` · IBS ${escapeHtml(r.cst_ibs || "—")} / CBS ${escapeHtml(r.cst_cbs || "—")}` : ""}`)}
          ${linha("ICMS", `base ${fmtMoney(r.base_icms)} · ${r.aliquota_icms}% · ${fmtMoney(r.valor_icms)}`)}
          ${linha("ICMS-ST", r.valor_icms_st ? `base ${fmtMoney(r.base_icms_st)} · ${r.aliquota_icms_st}% · ${fmtMoney(r.valor_icms_st)}` : "—")}
          ${linha("PIS / COFINS", `${fmtMoney(r.valor_pis)} / ${fmtMoney(r.valor_cofins)}`)}
          ${linha("IBS / CBS", `${fmtMoney(r.valor_ibs)} / ${fmtMoney(r.valor_cbs)}`)}
        </tbody></table>
      </div>
      <p style="font-size:12px;color:var(--ink-soft);margin:8px 0 0;">
        Regra: <b>${escapeHtml(String((r.memoria as Record<string, unknown>).regra_nome || "configuração do produto"))}</b>
        ${(r.memoria as Record<string, unknown>).versao ? `· versão ${escapeHtml(String((r.memoria as Record<string, unknown>).versao))}` : ""}
        ${r.memoria_produto ? `· Produto: <b>${escapeHtml(String((r.memoria_produto as Record<string, unknown>).regra_nome || ""))}</b>` : ""}
      </p>
      ${probs ? `<h4 style="margin:12px 0 4px;">Validação</h4><ul class="sim-probs">${probs}</ul>` : ""}
      <details class="sim-fiscal"><summary>Árvore de decisão (por que essa regra?)</summary>
        <ul class="sim-dec">${dec || "<li>—</li>"}</ul>
      </details>
    </div>`;
}

// ─── Sugestões de NCM (IBPT) ──────────────────────────────

async function renderSugestoes($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <div class="estq-filtros" style="align-items:flex-end;flex-wrap:wrap;">
      <div class="field"><label>Status</label>
        <select id="sgStatus"><option value="pendente">Pendentes</option><option value="aplicada">Aplicadas</option><option value="rejeitada">Rejeitadas</option><option value="">Todas</option></select>
      </div>
      <div class="field"><label>Confiança mín. %</label><input id="sgConf" type="number" min="0" max="100" step="1" placeholder="ex.: 50"></div>
      <div class="field" style="min-width:200px;"><label>Busca</label><input id="sgQ" placeholder="Produto, SKU, NCM…" autocomplete="off"></div>
      <button class="btn btn--ghost" id="sgFiltrar">Filtrar</button>
      <button class="btn btn--accent" id="sgGerar">Gerar sugestões</button>
      <button class="btn" id="sgAplicarTodas">Aplicar pendentes ≥ X%</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Produto</th><th>NCM sugerido</th><th>Descrição IBPT</th><th>Confiança</th><th>Status</th><th></th></tr></thead>
      <tbody id="tblSgBody"><tr><td colspan="6" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  const carregar = async () => {
    const $body = currentApp?.querySelector<HTMLElement>("#tblSgBody");
    if (!$body) return;
    const status = currentApp?.querySelector<HTMLSelectElement>("#sgStatus")?.value || "";
    const conf = parseFloat(currentApp?.querySelector<HTMLInputElement>("#sgConf")?.value || "0") || undefined;
    const q = (currentApp?.querySelector<HTMLInputElement>("#sgQ")?.value || "").trim() || undefined;
    try {
      const res = await api.listarSugestoesIbpt({ status, confianca_min: conf, q, limit: 200 });
      if (!res.length) { $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Nenhuma sugestão</td></tr>`; return; }
      $body.innerHTML = res.map((s) => `
        <tr>
          <td><strong>${escapeHtml(s.produto_nome)}</strong>${s.sku ? `<div style="font-size:11px;color:var(--ink-faint);font-family:var(--font-mono);">${escapeHtml(s.sku)}</div>` : ""}</td>
          <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(s.ncm)}</td>
          <td style="font-size:12px;color:var(--ink-soft);">${escapeHtml(s.descricao || "—")}</td>
          <td><span class="badge ${s.confianca >= 70 ? "badge--ok" : s.confianca >= 40 ? "badge--muted" : "badge--cancelada"}">${s.confianca.toFixed(0)}%</span></td>
          <td><span class="badge badge--${s.status === "aplicada" ? "ok" : s.status === "rejeitada" ? "cancelada" : "muted"}">${s.status}</span></td>
          <td class="cell-actions" style="gap:6px;">
            ${s.status === "pendente" ? `
              <button class="btn btn--sm" data-aplicar="${s.id}">Aplicar</button>
              <button class="btn btn--sm btn--ghost" data-rejeitar="${s.id}">Rejeitar</button>` : ""}
          </td>
        </tr>`).join("");
      $body.querySelectorAll<HTMLElement>("[data-aplicar]").forEach((b) => {
        b.addEventListener("click", async () => {
          try {
            await api.revisarSugestaoIbpt(Number(b.dataset.aplicar), "aplicada");
            toast("NCM aplicada", "success");
            await carregar();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        });
      });
      $body.querySelectorAll<HTMLElement>("[data-rejeitar]").forEach((b) => {
        b.addEventListener("click", async () => {
          try {
            await api.revisarSugestaoIbpt(Number(b.dataset.rejeitar), "rejeitada");
            toast("Sugestão rejeitada", "success");
            await carregar();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        });
      });
    } catch {
      $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Erro</td></tr>`;
    }
  };
  $ct.querySelector<HTMLElement>("#sgFiltrar")!.addEventListener("click", () => void carregar());
  $ct.querySelector<HTMLInputElement>("#sgQ")?.addEventListener("keydown", (e) => { if (e.key === "Enter") void carregar(); });
  $ct.querySelector<HTMLElement>("#sgGerar")!.addEventListener("click", async () => {
    const conf = parseFloat(currentApp?.querySelector<HTMLInputElement>("#sgConf")?.value || "40") || 40;
    try {
      const r = await api.gerarSugestoesIbpt({ confianca_min: conf });
      toast(`${r.sugestoes} sugestões geradas`, "success");
      await carregar();
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  });
  $ct.querySelector<HTMLElement>("#sgAplicarTodas")!.addEventListener("click", async () => {
    const conf = parseFloat(currentApp?.querySelector<HTMLInputElement>("#sgConf")?.value || "0") || 0;
    if (!(await confirmDialog(`Aplicar TODAS as sugestões pendentes com confiança ≥ ${conf}%?`))) return;
    try {
      const r = await api.aplicarSugestoesIbpt({ confianca_min: conf });
      toast(`${r.aplicadas} NCMs aplicadas`, "success");
      await carregar();
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  });
  await carregar();
}
