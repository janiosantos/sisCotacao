// pages/plano_contas.ts — plano de contas (receitas e despesas).

import { api, type ContaPlano, type ContaPlanoPayload } from "../api/client";
import { escapeHtml } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

const TIPOS: { valor: "receita" | "despesa"; rotulo: string }[] = [
  { valor: "receita", rotulo: "Receita" },
  { valor: "despesa", rotulo: "Despesa" },
];

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando plano de contas…</div>`;
  let contas: ContaPlano[] = [];
  try {
    contas = await api.listarPlanoContas();
  } catch (e) {
    toast("Erro ao carregar plano de contas: " + (e as Error).message, "error");
  }

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Plano de contas</h1>
        <p class="page-sub">Contas para classificar receitas e despesas do negócio.</p>
      </div>
      <button class="btn btn--accent" id="btnNovo">+ Nova conta</button>
    </div>
    <div id="tabelaWrap"></div>
  `;

  const $t = $app.querySelector<HTMLElement>("#tabelaWrap")!;
  $t.innerHTML = contasTabela(contas);

  $app.querySelector<HTMLButtonElement>("#btnNovo")!.addEventListener("click", () => abrirModal($app, null));
  $app.querySelectorAll<HTMLElement>("[data-edit]").forEach((b) => {
    b.addEventListener("click", () => {
      const c = contas.find((x) => x.id === Number(b.dataset.edit))!;
      abrirModal($app, c);
    });
  });
  $app.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
    b.addEventListener("click", async () => {
      const c = contas.find((x) => x.id === Number(b.dataset.toggle))!;
      await api.alternarAtivoContaPlano(c.id, !c.ativo);
      await render($app);
    });
  });
}

function contasTabela(contas: ContaPlano[]): string {
  if (!contas.length) {
    return `<div class="empty-box"><p>Nenhuma conta cadastrada</p><p>Cadastre a primeira conta para começar.</p></div>`;
  }
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Código</th><th>Nome</th><th>Tipo</th><th>Status</th><th></th></tr></thead>
        <tbody>
          ${contas.map((c) => `
            <tr>
              <td style="font-family:var(--font-mono);font-size:12.5px;">${escapeHtml(c.codigo)}</td>
              <td>${escapeHtml(c.nome)}</td>
              <td><span class="badge ${c.tipo === "receita" ? "badge--fechada" : "badge--cancelada"}">${escapeHtml(c.tipo)}</span></td>
              <td><span class="badge ${c.ativo ? "badge--fechada" : "badge--cancelada"}">${c.ativo ? "Ativo" : "Inativo"}</span></td>
              <td style="display:flex;gap:6px;justify-content:flex-end;">
                <button class="btn btn--sm" data-edit="${c.id}">Editar</button>
                <button class="btn btn--sm btn--ghost" data-toggle="${c.id}">${c.ativo ? "Desativar" : "Ativar"}</button>
              </td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function abrirModal($app: HTMLElement, conta: ContaPlano | null): void {
  const isEdit = !!conta;
  openModal(
    `<div class="modal-head"><h3>${isEdit ? "Editar" : "Nova"} conta</h3><button class="icon-btn" data-close>×</button></div>
     <div style="display:flex;flex-direction:column;gap:14px;">
       <div class="field"><label>Código *</label><input id="mCodigo" value="${escapeHtml(conta?.codigo || "")}" placeholder="Ex.: 1.01"></div>
       <div class="field"><label>Nome *</label><input id="mNome" value="${escapeHtml(conta?.nome || "")}"></div>
       <div class="field"><label>Tipo</label>
         <select id="mTipo">
           ${TIPOS.map((t) => `<option value="${t.valor}" ${conta?.tipo === t.valor ? "selected" : ""}>${t.rotulo}</option>`).join("")}
         </select>
       </div>
     </div>
     <div class="modal-actions">
       <button class="btn" data-close>Cancelar</button>
       <button class="btn btn--accent" id="btnSalvar">Salvar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLButtonElement>("#btnSalvar")!.onclick = async () => {
          const codigo = modal.querySelector<HTMLInputElement>("#mCodigo")!.value.trim();
          const nome = modal.querySelector<HTMLInputElement>("#mNome")!.value.trim();
          const tipo = modal.querySelector<HTMLSelectElement>("#mTipo")!.value as "receita" | "despesa";
          if (!codigo || !nome) { toast("Informe código e nome da conta", "error"); return; }
          const payload: ContaPlanoPayload = { codigo, nome, tipo };
          try {
            if (isEdit && conta) await api.atualizarContaPlano(conta.id, payload);
            else await api.criarContaPlano(payload);
            closeModal();
            toast("Conta salva", "success");
            await render($app);
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}