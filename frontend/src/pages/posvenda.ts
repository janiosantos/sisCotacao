import "../styles/estoque.css";
import { api, type ClienteInteracao, type Garantia } from "../api/client";
import { escapeHtml, fmtDate } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;
let abaAtiva = "acompanhamento";

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  paint();
  await carregarAba();
}

function paint(): void {
  if (!currentApp) return;
  currentApp.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Pós-venda</h1>
      <p class="page-sub">Acompanhamento de clientes e garantia.</p>
    </div>
    <div class="tab-bar">
      <button class="tab-btn ${abaAtiva === "acompanhamento" ? "is-active" : ""}" data-aba="acompanhamento">Acompanhamento</button>
      <button class="tab-btn ${abaAtiva === "garantia" ? "is-active" : ""}" data-aba="garantia">Garantia</button>
    </div>
    <div id="posContent" class="estq-content"></div>
  `;
  currentApp.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      abaAtiva = btn.dataset.aba || "acompanhamento";
      paint();
      void carregarAba();
    });
  });
}

async function carregarAba(): Promise<void> {
  const $ct = currentApp?.querySelector<HTMLElement>("#posContent");
  if (!$ct) return;
  if (abaAtiva === "acompanhamento") await renderAcompanhamento($ct);
  else if (abaAtiva === "garantia") await renderGarantia($ct);
}

// ──────────────────────────────────────────────────────────
//  Acompanhamento
// ──────────────────────────────────────────────────────────

async function renderAcompanhamento($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaInteracao">Nova interação</button></p>
    <div class="estq-filtros">
      <div class="field"><label>Cliente ID</label><input id="filtroCliId" type="number" min="1" placeholder="ID do cliente"></div>
      <div class="field"><label>Pendentes</label><input id="filtroPend" type="checkbox" style="width:auto;"></div>
      <button class="btn btn--ghost" id="btnFiltrarInt">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Data</th><th>Cliente</th><th>Tipo</th><th>Descrição</th><th>Próx. contato</th></tr></thead>
      <tbody id="tblIntBody"><tr><td colspan="5" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaInteracao")!.addEventListener("click", () => abrirModalInteracao(null));
  $ct.querySelector<HTMLElement>("#btnFiltrarInt")!.addEventListener("click", () => void carregarInteracoes());
  await carregarInteracoes();
}

async function carregarInteracoes(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblIntBody");
  if (!$body) return;
  const cliente_id = parseInt((currentApp?.querySelector<HTMLInputElement>("#filtroCliId")?.value || ""), 10) || undefined;
  const pendentes = (currentApp?.querySelector<HTMLInputElement>("#filtroPend") as HTMLInputElement)?.checked || false;
  try {
    const res = await api.listarInteracoes({ cliente_id, pendentes });
    if (!res.length) { $body.innerHTML = `<tr><td colspan="5" class="pdv-sem-res">Nenhuma interação</td></tr>`; return; }
    $body.innerHTML = res.map((i) => `
      <tr>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(i.data_contato)}</td>
        <td><strong>${escapeHtml(i.cliente_nome)}</strong></td>
        <td><span class="badge badge--muted">${i.tipo}</span></td>
        <td>${escapeHtml(i.descricao)}</td>
        <td style="font-size:12px;color:${i.data_proximo_contato ? "var(--accent-ink)" : "var(--ink-faint)"};">${i.data_proximo_contato ? fmtDate(i.data_proximo_contato) : "—"}</td>
      </tr>`).join("");
  } catch {
    $body.innerHTML = `<tr><td colspan="5" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalInteracao(_interacao: ClienteInteracao | null): void {
  const tipos = ["ligacao", "visita", "email", "whatsapp", "follow_up", "outro"];
  const opts = tipos.map((t) => `<option value="${t}">${t}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>Nova interação</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Cliente</label><input id="intCliente" placeholder="Nome" autocomplete="off"></div>
       <div class="field"><label>Tipo</label><select id="intTipo">${opts}</select></div>
       <div class="field"><label>Data do contato</label><input id="intData" type="date"></div>
       <div class="field"><label>Descrição</label><textarea id="intDesc" rows="3"></textarea></div>
       <div class="field"><label>Próximo contato (opcional)</label><input id="intProx" type="date"></div>
       <div class="field"><label>Orçamento ID (opcional)</label><input id="intOrcId" type="number" min="1"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="intSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#intSalvar")!.onclick = async () => {
          try {
            await api.criarInteracao({
              cliente_nome: (m.querySelector<HTMLInputElement>("#intCliente")?.value || "").trim(),
              tipo: m.querySelector<HTMLSelectElement>("#intTipo")?.value || "ligacao",
              data_contato: m.querySelector<HTMLInputElement>("#intData")?.value || "",
              descricao: (m.querySelector<HTMLInputElement>("#intDesc")?.value || "").trim(),
              data_proximo_contato: m.querySelector<HTMLInputElement>("#intProx")?.value || undefined,
              orcamento_id: parseInt(m.querySelector<HTMLInputElement>("#intOrcId")?.value || "", 10) || undefined,
            });
            toast("Interação registrada", "success");
            closeModal();
            await carregarInteracoes();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Garantia
// ──────────────────────────────────────────────────────────

async function renderGarantia($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaGarantia">Nova garantia</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Cliente</th><th>Produto</th><th>Início</th><th>Fim</th><th>Dias</th><th>Status</th><th></th></tr></thead>
      <tbody id="tblGarBody"><tr><td colspan="7" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaGarantia")!.addEventListener("click", () => abrirModalGarantia(null));
  await carregarGarantias();
}

async function carregarGarantias(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblGarBody");
  if (!$body) return;
  try {
    const res = await api.listarGarantias();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Nenhuma garantia</td></tr>`; return; }
    $body.innerHTML = res.map((g) => `
      <tr>
        <td><strong>${escapeHtml(g.cliente_nome)}</strong></td>
        <td>${escapeHtml(g.produto_nome)}</td>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(g.data_inicio)}</td>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(g.data_fim)}</td>
        <td>${g.dias}</td>
        <td><span class="badge badge--${g.status === "ativa" ? "ok" : g.status === "vencida" ? "muted" : "erro"}">${g.status}</span></td>
        <td class="cell-actions">
          <button class="btn btn--ghost btn--sm" data-status="${g.id}">Alterar status</button>
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-status]").forEach((b) => {
      b.addEventListener("click", async () => {
        const g = res.find((x) => x.id === Number(b.dataset.status));
        if (g) {
          const novos = { ativa: "acionada", acionada: "cancelada", cancelada: "ativa", vencida: "ativa" };
          const novo = novos[g.status as keyof typeof novos] || "ativa";
          try {
            await api.atualizarStatusGarantia(g.id, novo);
            toast(`Status alterado para ${novo}`, "success");
            await carregarGarantias();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        }
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalGarantia(_g: Garantia | null): void {
  openModal(
    `<div class="modal-head"><h3>Nova garantia</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Cliente</label><input id="gaCliente" autocomplete="off"></div>
       <div class="field"><label>Produto</label><input id="gaProduto" autocomplete="off"></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Data início</label><input id="gaInicio" type="date"></div>
         <div class="field" style="flex:1"><label>Data fim</label><input id="gaFim" type="date"></div>
       </div>
       <div class="field"><label>Dias</label><input id="gaDias" type="number" value="90"></div>
       <div class="field"><label>Descrição</label><textarea id="gaDesc" rows="2"></textarea></div>
       <div class="field"><label>Observação</label><textarea id="gaObs" rows="2"></textarea></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="gaSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#gaSalvar")!.onclick = async () => {
          try {
            await api.criarGarantia({
              cliente_nome: (m.querySelector<HTMLInputElement>("#gaCliente")?.value || "").trim(),
              produto_nome: (m.querySelector<HTMLInputElement>("#gaProduto")?.value || "").trim(),
              data_inicio: m.querySelector<HTMLInputElement>("#gaInicio")?.value || "",
              data_fim: m.querySelector<HTMLInputElement>("#gaFim")?.value || "",
              dias: parseInt(m.querySelector<HTMLInputElement>("#gaDias")?.value || "90", 10),
              descricao: (m.querySelector<HTMLInputElement>("#gaDesc")?.value || "").trim() || undefined,
              observacao: (m.querySelector<HTMLInputElement>("#gaObs")?.value || "").trim() || undefined,
            });
            toast("Garantia registrada", "success");
            closeModal();
            await carregarGarantias();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}
