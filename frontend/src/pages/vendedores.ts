// pages/vendedores.ts — cadastro de vendedores.

import { api, type Vendedor, type VendedorPayload } from "../api/client";
import { escapeHtml } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando vendedores…</div>`;
  let vendedores: Vendedor[] = [];
  try {
    vendedores = await api.listarVendedores();
  } catch (e) {
    toast("Erro ao carregar vendedores: " + (e as Error).message, "error");
  }

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Vendedores</h1>
        <p class="page-sub">Cadastro usado para vincular clientes e medir comissão sobre vendas.</p>
      </div>
      <button class="btn btn--accent" id="btnNovo">+ Novo vendedor</button>
    </div>
    <div id="tabelaWrap"></div>
  `;

  const $t = $app.querySelector<HTMLElement>("#tabelaWrap")!;
  $t.innerHTML = vendedoresTabela(vendedores);

  $app.querySelector<HTMLButtonElement>("#btnNovo")!.addEventListener("click", () => abrirModal($app, null));
  $app.querySelectorAll<HTMLElement>("[data-edit]").forEach((b) => {
    b.addEventListener("click", () => {
      const v = vendedores.find((x) => x.id === Number(b.dataset.edit))!;
      abrirModal($app, v);
    });
  });
  $app.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
    b.addEventListener("click", async () => {
      const v = vendedores.find((x) => x.id === Number(b.dataset.toggle))!;
      await api.alternarAtivoVendedor(v.id, !v.ativo);
      await render($app);
    });
  });
}

function vendedoresTabela(vendedores: Vendedor[]): string {
  if (!vendedores.length) {
    return `<div class="empty-box"><p>Nenhum vendedor cadastrado</p><p>Cadastre o primeiro para começar.</p></div>`;
  }
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Nome</th><th>Comissão</th><th>Status</th><th></th></tr></thead>
        <tbody>
          ${vendedores.map((v) => `
            <tr>
              <td>${escapeHtml(v.nome)}</td>
              <td>${v.comissao_pct}%</td>
              <td><span class="badge ${v.ativo ? "badge--fechada" : "badge--cancelada"}">${v.ativo ? "Ativo" : "Inativo"}</span></td>
              <td style="display:flex;gap:6px;justify-content:flex-end;">
                <button class="btn btn--sm" data-edit="${v.id}">Editar</button>
                <button class="btn btn--sm btn--ghost" data-toggle="${v.id}">${v.ativo ? "Desativar" : "Ativar"}</button>
              </td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function abrirModal($app: HTMLElement, vendedor: Vendedor | null): void {
  const isEdit = !!vendedor;
  openModal(
    `<div class="modal-head"><h3>${isEdit ? "Editar" : "Novo"} vendedor</h3><button class="icon-btn" data-close>×</button></div>
     <div style="display:flex;flex-direction:column;gap:14px;">
       <div class="field"><label>Nome *</label><input id="mNome" value="${escapeHtml(vendedor?.nome || "")}"></div>
       <div class="field"><label>Comissão (%)</label><input id="mComissao" type="number" min="0" step="0.01" value="${vendedor?.comissao_pct ?? ""}"></div>
     </div>
     <div class="modal-actions">
       <button class="btn" data-close>Cancelar</button>
       <button class="btn btn--accent" id="btnSalvar">Salvar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLButtonElement>("#btnSalvar")!.onclick = async () => {
          const nome = modal.querySelector<HTMLInputElement>("#mNome")!.value.trim();
          if (!nome) { toast("Informe o nome do vendedor", "error"); return; }
          const payload: VendedorPayload = {
            nome,
            comissao_pct: Number(modal.querySelector<HTMLInputElement>("#mComissao")!.value) || 0,
          };
          try {
            if (isEdit && vendedor) await api.atualizarVendedor(vendedor.id, payload);
            else await api.criarVendedor(payload);
            closeModal();
            toast("Vendedor salvo", "success");
            await render($app);
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}