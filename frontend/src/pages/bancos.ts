import "../styles/estoque.css";
import { api, type ContaBancaria, type ContaBancariaPayload, type MovimentoBancarioPayload } from "../api/client";
import { escapeHtml, fmtDate, fmtMoney } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;
let abaAtiva = "contas";

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  paint();
  await carregarAba();
}

function paint(): void {
  if (!currentApp) return;
  currentApp.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Bancos</h1>
      <p class="page-sub">Contas bancárias, extrato e conciliação.</p>
    </div>
    <div class="tab-bar">
      <button class="tab-btn ${abaAtiva === "contas" ? "is-active" : ""}" data-aba="contas">Contas</button>
      <button class="tab-btn ${abaAtiva === "extrato" ? "is-active" : ""}" data-aba="extrato">Extrato</button>
    </div>
    <div id="bancContent" class="estq-content"></div>
  `;
  currentApp.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      abaAtiva = btn.dataset.aba || "contas";
      paint();
      void carregarAba();
    });
  });
}

async function carregarAba(): Promise<void> {
  const $ct = currentApp?.querySelector<HTMLElement>("#bancContent");
  if (!$ct) return;
  if (abaAtiva === "contas") await renderContas($ct);
  else if (abaAtiva === "extrato") await renderExtrato($ct);
}

// ──────────────────────────────────────────────────────────
//  Contas
// ──────────────────────────────────────────────────────────

async function renderContas($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaConta">Nova conta bancária</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Nome</th><th>Banco</th><th>Agência</th><th>Conta</th><th>Saldo</th><th>Status</th><th></th></tr></thead>
      <tbody id="tblContasBody"><tr><td colspan="7" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaConta")!.addEventListener("click", () => abrirModalConta(null));
  await carregarContas();
}

async function carregarContas(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblContasBody");
  if (!$body) return;
  try {
    const res = await api.listarContasBancarias();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Nenhuma conta</td></tr>`; return; }
    $body.innerHTML = res.map((c) => `
      <tr>
        <td><strong>${escapeHtml(c.nome)}</strong></td>
        <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(c.banco)}</td>
        <td>${escapeHtml(c.agencia)}</td>
        <td style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(c.conta)}-${escapeHtml(c.digito)}</td>
        <td><strong>${fmtMoney(c.saldo_atual)}</strong></td>
        <td><span class="badge badge--${c.ativo ? "ok" : "muted"}">${c.ativo ? "Ativa" : "Inativa"}</span></td>
        <td class="cell-actions">
          <button class="btn btn--ghost btn--sm" data-editar="${c.id}">Editar</button>
          <button class="btn btn--ghost btn--sm" data-toggle="${c.id}">${c.ativo ? "Desat." : "Ativar"}</button>
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-editar]").forEach((b) => {
      b.addEventListener("click", () => {
        const c = res.find((x) => x.id === Number(b.dataset.editar));
        if (c) abrirModalConta(c);
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
      b.addEventListener("click", async () => {
        const c = res.find((x) => x.id === Number(b.dataset.toggle));
        if (c) { await api.alternarAtivoContaBancaria(c.id, !c.ativo); await carregarContas(); }
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalConta(conta: ContaBancaria | null): void {
  const editando = !!conta;
  openModal(
    `<div class="modal-head"><h3>${editando ? "Editar" : "Nova"} conta bancária</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Nome</label><input id="bcNome" value="${escapeHtml(conta?.nome || "")}" autocomplete="off"></div>
       <div class="field-row">
         <div class="field" style="flex:0.6"><label>Banco (código)</label><input id="bcBanco" value="${conta?.banco || "000"}" maxlength="3"></div>
         <div class="field" style="flex:1"><label>Agência</label><input id="bcAgencia" value="${escapeHtml(conta?.agencia || "")}" maxlength="10"></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Conta</label><input id="bcConta" value="${escapeHtml(conta?.conta || "")}" maxlength="15"></div>
         <div class="field" style="flex:0.4"><label>Dígito</label><input id="bcDigito" value="${escapeHtml(conta?.digito || "")}" maxlength="2"></div>
       </div>
       ${editando ? "" : `<div class="field"><label>Saldo inicial</label><input id="bcSaldo" type="number" step="0.01" value="0"></div>`}
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="bcSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#bcSalvar")!.onclick = async () => {
          const payload: ContaBancariaPayload = {
            nome: (m.querySelector<HTMLInputElement>("#bcNome")?.value || "").trim(),
            banco: m.querySelector<HTMLInputElement>("#bcBanco")?.value || "000",
            agencia: m.querySelector<HTMLInputElement>("#bcAgencia")?.value || "",
            conta: m.querySelector<HTMLInputElement>("#bcConta")?.value || "",
            digito: m.querySelector<HTMLInputElement>("#bcDigito")?.value || "",
            ...(editando ? {} : { saldo_inicial: parseFloat((m.querySelector<HTMLInputElement>("#bcSaldo")?.value || "0").replace(",", ".")) }),
          };
          if (!payload.nome) { toast("Informe o nome", "error"); return; }
          try {
            if (editando) await api.atualizarContaBancaria(conta!.id, payload);
            else await api.criarContaBancaria(payload);
            toast(editando ? "Conta atualizada" : "Conta criada", "success");
            closeModal();
            await carregarContas();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Extrato
// ──────────────────────────────────────────────────────────

async function renderExtrato($ct: HTMLElement): Promise<void> {
  let contas: ContaBancaria[] = [];
  try {
    contas = await api.listarContasBancarias();
  } catch { /* */ }
  const opts = contas.map((c) => `<option value="${c.id}">${escapeHtml(c.nome)} (${c.banco})</option>`).join("");
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovoMov">Novo movimento</button></p>
    <div class="estq-filtros">
      <div class="field"><label>Conta</label>
        <select id="filtroExtConta"><option value="">Todas</option>${opts}</select>
      </div>
      <button class="btn btn--ghost" id="btnFiltrarExt">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Data</th><th>Conta</th><th>Tipo</th><th>Descrição</th><th>Valor</th><th>Doc</th><th>Conc.</th><th></th></tr></thead>
      <tbody id="tblExtBody"><tr><td colspan="8" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovoMov")!.addEventListener("click", () => abrirModalMovimento(contas));
  $ct.querySelector<HTMLElement>("#btnFiltrarExt")!.addEventListener("click", () => void carregarExtrato());
  await carregarExtrato();
}

async function carregarExtrato(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblExtBody");
  if (!$body) return;
  const conta_id = (currentApp?.querySelector<HTMLSelectElement>("#filtroExtConta")?.value || "").trim() || undefined;
  try {
    const res = await api.listarMovimentosBancarios({ conta_id: conta_id ? Number(conta_id) : undefined });
    if (!res.length) { $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Nenhum movimento</td></tr>`; return; }
    $body.innerHTML = res.map((m) => `
      <tr>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(m.data_movimento)}</td>
        <td>${escapeHtml(m.conta_nome)}</td>
        <td><span class="badge badge--${m.tipo === "credito" ? "ok" : "erro"}">${m.tipo}</span></td>
        <td>${escapeHtml(m.descricao)}</td>
        <td><strong>${fmtMoney(m.valor)}</strong></td>
        <td style="font-size:11px;font-family:var(--font-mono);">${escapeHtml(m.documento || "")}</td>
        <td>${m.conciliado ? "✓" : "—"}</td>
        <td class="cell-actions">
          <button class="btn btn--ghost btn--sm" data-conciliar="${m.id}">${m.conciliado ? "Desconc." : "Conciliar"}</button>
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-conciliar]").forEach((b) => {
      b.addEventListener("click", async () => {
        try {
          await api.toggleConciliado(Number(b.dataset.conciliar));
          toast("Conciliado alternado", "success");
          await carregarExtrato();
        } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalMovimento(contas: ContaBancaria[]): void {
  const opts = contas.map((c) => `<option value="${c.id}">${escapeHtml(c.nome)}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>Novo movimento bancário</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Conta</label><select id="mvConta">${opts}</select></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Tipo</label>
           <select id="mvTipo"><option value="credito">Crédito</option><option value="debito">Débito</option><option value="transferencia">Transferência</option></select>
         </div>
         <div class="field" style="flex:1"><label>Valor</label><input id="mvValor" type="number" step="0.01" min="0.01"></div>
       </div>
       <div class="field"><label>Data</label><input id="mvData" type="date"></div>
       <div class="field"><label>Descrição</label><input id="mvDesc" autocomplete="off"></div>
       <div class="field"><label>Documento</label><input id="mvDoc" autocomplete="off"></div>
       <div class="field"><label>Categoria</label><input id="mvCat" autocomplete="off"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="mvSalvar">Registrar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#mvSalvar")!.onclick = async () => {
          const payload: MovimentoBancarioPayload = {
            conta_id: parseInt(m.querySelector<HTMLSelectElement>("#mvConta")?.value || "0", 10),
            tipo: m.querySelector<HTMLSelectElement>("#mvTipo")?.value || "credito",
            valor: parseFloat((m.querySelector<HTMLInputElement>("#mvValor")?.value || "0").replace(",", ".")),
            data_movimento: m.querySelector<HTMLInputElement>("#mvData")?.value || "",
            descricao: (m.querySelector<HTMLInputElement>("#mvDesc")?.value || "").trim() || undefined,
            documento: (m.querySelector<HTMLInputElement>("#mvDoc")?.value || "").trim() || undefined,
            categoria: (m.querySelector<HTMLInputElement>("#mvCat")?.value || "").trim() || undefined,
          };
          if (!payload.conta_id || payload.valor <= 0 || !payload.data_movimento) {
            toast("Preencha conta, valor e data", "error"); return;
          }
          try {
            const r = await api.criarMovimentoBancario(payload);
            toast(`Movimento registrado. Saldo: ${fmtMoney(r.saldo_atual)}`, "success");
            closeModal();
            await carregarExtrato();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}
