// pages/unidades.ts — CRUD de unidades de compra predefinidas (opções do
// campo "Unid. compra" no cadastro de produtos x fornecedores).
import { api, type UnidadeCompra } from "../api/client";
import { escapeHtml } from "../ui/format";
import { confirmDialog, toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  let unidades: UnidadeCompra[];
  try {
    unidades = await api.listarUnidadesCompra();
  } catch (e) {
    toast("Erro ao carregar unidades: " + (e as Error).message, "error");
    unidades = [];
  }
  renderTela(unidades);
}

function renderTela(unidades: UnidadeCompra[]): void {
  if (!currentApp) return;
  const ativas = unidades.filter((u) => u.ativo).length;
  currentApp.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Unidades de compra</h1>
        <p class="page-sub">Unidades disponíveis para "Unid. compra" no cadastro de produtos por fornecedor.</p>
      </div>
      <button class="btn btn--accent" id="btnNovaUnidade">+ Nova unidade</button>
    </div>
    <div class="toolbar">
      <span class="result-count">${unidades.length} unidades (${ativas} ativas)</span>
    </div>
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Sigla</th><th>Descrição</th><th>Status</th><th></th></tr></thead>
        <tbody>
          ${unidades.length ? unidades.map(rowHtml).join("") : '<tr><td colspan="4" style="text-align:center;color:var(--ink-faint);">Nenhuma unidade cadastrada</td></tr>'}
        </tbody>
      </table>
    </div>
  `;

  const $btnNova = currentApp.querySelector<HTMLButtonElement>("#btnNovaUnidade");
  if ($btnNova) $btnNova.onclick = () => abrirModal(null);
  currentApp.querySelectorAll<HTMLElement>("[data-un-edit]").forEach((btn) => {
    const id = Number(btn.dataset.unEdit);
    btn.onclick = () => {
      const u = unidades.find((x) => x.id === id);
      if (u) abrirModal(u);
    };
  });
  currentApp.querySelectorAll<HTMLElement>("[data-un-toggle]").forEach((btn) => {
    btn.onclick = async () => {
      const u = unidades.find((x) => x.id === Number(btn.dataset.unToggle));
      if (!u) return;
      try {
        await api.atualizarUnidadeCompra(u.id, u.sigla, u.descricao, !u.ativo);
        toast(u.ativo ? "Unidade desativada" : "Unidade ativada", "success");
        await render(currentApp!);
      } catch (e) {
        toast("Erro: " + (e as Error).message, "error");
      }
    };
  });
  currentApp.querySelectorAll<HTMLElement>("[data-un-del]").forEach((btn) => {
    btn.onclick = async () => {
      const u = unidades.find((x) => x.id === Number(btn.dataset.unDel));
      if (!u) return;
      if (!(await confirmDialog(`Excluir a unidade "${u.sigla}"?`))) return;
      try {
        await api.excluirUnidadeCompra(u.id);
        toast("Unidade excluída", "success");
        await render(currentApp!);
      } catch (e) {
        toast("Erro: " + (e as Error).message, "error");
      }
    };
  });
}

function rowHtml(u: UnidadeCompra): string {
  return `
    <tr>
      <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(u.sigla)}</td>
      <td>${escapeHtml(u.descricao) || "—"}</td>
      <td><span class="badge badge--${u.ativo ? "respondido" : "cancelada"}">${u.ativo ? "Ativa" : "Inativa"}</span></td>
      <td>
        <button class="btn btn--sm btn--ghost" data-un-edit="${u.id}">Editar</button>
        <button class="btn btn--sm btn--ghost" data-un-toggle="${u.id}">${u.ativo ? "Desativar" : "Ativar"}</button>
        <button class="btn btn--sm btn--ghost btn--danger" data-un-del="${u.id}">Excluir</button>
      </td>
    </tr>`;
}

function abrirModal(u: UnidadeCompra | null): void {
  const modal = document.createElement("div");
  modal.className = "modal-overlay";
  modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-head"><h3>${u ? "Editar unidade" : "Nova unidade"}</h3><button class="icon-btn" data-close>×</button></div>
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div class="field"><label>Sigla *</label><input id="mSigla" placeholder="Ex.: CX, PCT, RL" value="${u ? escapeHtml(u.sigla) : ""}" maxlength="10"></div>
        <div class="field"><label>Descrição</label><input id="mDesc" placeholder="Ex.: Caixa, Pacote, Rolo" value="${u ? escapeHtml(u.descricao) : ""}"></div>
      </div>
      <div class="modal-actions">
        <button class="btn" data-close>Cancelar</button>
        <button class="btn btn--accent" id="btnSalvar">Salvar</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.querySelectorAll<HTMLElement>("[data-close]").forEach((b) => (b.onclick = () => modal.remove()));
  const $sigla = modal.querySelector<HTMLInputElement>("#mSigla")!;
  $sigla.focus();
  modal.querySelector<HTMLButtonElement>("#btnSalvar")!.onclick = async () => {
    const sigla = $sigla.value.trim().toUpperCase();
    const descricao = modal.querySelector<HTMLInputElement>("#mDesc")!.value.trim();
    if (!sigla) { toast("Informe a sigla", "error"); return; }
    try {
      if (u) {
        await api.atualizarUnidadeCompra(u.id, sigla, descricao, u.ativo);
        toast("Unidade atualizada", "success");
      } else {
        await api.criarUnidadeCompra(sigla, descricao);
        toast("Unidade criada", "success");
      }
      modal.remove();
      await render(currentApp!);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };
}