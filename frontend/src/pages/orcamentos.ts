// pages/orcamentos.ts — lista de orçamentos de venda salvos (PDV).
import { api, type OrcamentoLista } from "../api/client";
import { escapeHtml, fmtDate, fmtMoney } from "../ui/format";
import { closeModal, confirmDialog, openModal, toast } from "../ui/dom";

let currentFilter = "";
let appRef: HTMLElement | null = null;

const STATUS_LABELS: Record<string, string> = {
  rascunho: "Rascunho",
  ativo: "Ativo",
  em_analise: "Em análise",
  liberado: "Liberado",
  faturado: "Faturado",
  cancelado: "Cancelado",
};

export async function render($app: HTMLElement): Promise<void> {
  appRef = $app;
  $app.innerHTML = `<div class="loading">Carregando orçamentos…</div>`;
  let lista: OrcamentoLista[] = [];
  try {
    lista = await api.listarOrcamentos(currentFilter);
  } catch (e) {
    toast("Erro ao carregar orçamentos: " + (e as Error).message, "error");
  }

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Orçamentos</h1>
        <p class="page-sub">Orçamentos de venda montados no PDV.</p>
      </div>
      <a class="btn btn--accent" href="#/pdv">+ Novo orçamento</a>
    </div>

    <div class="toolbar">
      <div class="field">
        <label>Status</label>
        <select id="fStatus">
          <option value="">Todos</option>
          ${Object.entries(STATUS_LABELS)
            .map(([k, v]) => `<option value="${k}">${v}</option>`)
            .join("")}
        </select>
      </div>
      <span class="result-count">${lista.length} orçamento(s)</span>
    </div>

    ${lista.length === 0 ? vazio() : tabela(lista)}
  `;

  $app.querySelector<HTMLSelectElement>("#fStatus")!.value = currentFilter;
  $app.querySelector<HTMLSelectElement>("#fStatus")!.addEventListener("change", (e) => {
    currentFilter = (e.target as HTMLSelectElement).value;
    render($app);
  });
  $app.querySelectorAll<HTMLElement>("tr[data-id]").forEach((tr) => {
    tr.addEventListener("click", () => void abrirDetalhe(Number(tr.dataset.id)));
  });
}

function vazio(): string {
  return `<div class="empty-box"><p>Nenhum orçamento ainda</p><p>Monte um orçamento de venda no <a href="#/pdv">PDV</a>.</p></div>`;
}

function tabela(lista: OrcamentoLista[]): string {
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>Nº</th><th>Cliente</th><th>Contato</th><th>Status</th><th>Desconto</th><th>Itens</th><th>Total</th><th>Criada em</th><th></th>
        </tr></thead>
        <tbody>
          ${lista
            .map(
              (o) => `
              <tr data-id="${o.id}" class="row-link">
                <td style="font-family:var(--font-mono);">${escapeHtml(o.numero)}</td>
                <td>${escapeHtml(o.cliente || "—")}</td>
                <td>${escapeHtml(o.contato || "—")}</td>
                <td><span class="badge badge--${escapeHtml(o.status)}">${STATUS_LABELS[o.status] || o.status}</span></td>
                <td>${o.desconto_autorizado ? `<span class="badge badge--fechada" title="Desconto autorizado pelo gerente">Autorizado</span>` : "—"}</td>
                <td>${o.n_itens}</td>
                <td><strong>${fmtMoney(o.total)}</strong></td>
                <td>${fmtDate(o.criado_em)}</td>
                <td>
                  <a class="btn btn--sm" target="_blank" href="/orcamentos/venda/${o.id}/imprimir" title="Imprimir / salvar PDF">PDF</a>
                  <button class="btn btn--sm btn--ghost" data-status="${o.id}" title="Alterar status">⚙</button>
                </td>
              </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
}

async function abrirDetalhe(id: number): Promise<void> {
  let d;
  try {
    d = await api.detalharOrcamento(id);
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
    return;
  }
  const statusOpcoes = Object.entries(STATUS_LABELS)
    .map(([k, v]) => `<option value="${k}" ${d.status === k ? "selected" : ""}>${v}</option>`)
    .join("");
  openModal(
    `<div class="modal-head"><h3>${escapeHtml(d.numero)}</h3><button class="icon-btn" data-close>×</button></div>
     <p style="margin:-4px 0 12px;font-size:13px;color:var(--ink-soft);">${escapeHtml(d.cliente || "Sem cliente")}${d.contato ? " · " + escapeHtml(d.contato) : ""} · criado em ${fmtDate(d.criado_em)}</p>
     <div class="field">
       <label>Status</label>
       <select id="dStatus">${statusOpcoes}</select>
     </div>
     <div class="table-wrap">
       <table class="data-table">
         <thead><tr><th>Produto</th><th>Qtd.</th><th>Preço</th><th>Desc. %</th><th>Subtotal</th></tr></thead>
         <tbody>
           ${d.itens.map((i) => `
             <tr>
               <td>${escapeHtml(i.nome)}${i.sku ? `<div style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">${escapeHtml(i.sku)}</div>` : ""}</td>
               <td>${i.quantidade}</td>
               <td>${fmtMoney(i.preco_unitario)}</td>
               <td>${i.desconto_percentual || 0}%</td>
               <td><strong>${fmtMoney(i.subtotal || 0)}</strong></td>
             </tr>`).join("")}
         </tbody>
       </table>
     </div>
     <div style="display:flex;justify-content:flex-end;gap:16px;margin-top:14px;font-size:13.5px;flex-wrap:wrap;">
       <div>Subtotal: <strong>${fmtMoney(d.subtotal)}</strong></div>
       <div>Desconto: <strong>${fmtMoney(d.desconto)}</strong></div>
       <div>Total: <strong>${fmtMoney(d.total)}</strong></div>
     </div>
     ${d.desconto_autorizado
       ? `<p style="font-size:12.5px;color:var(--green);margin:10px 0 0;">✓ Desconto autorizado${d.desconto_autorizado_nome ? ` por ${escapeHtml(d.desconto_autorizado_nome)}` : ""}${d.desconto_autorizado_em ? ` em ${fmtDate(d.desconto_autorizado_em)}` : ""}.</p>`
       : `<button class="btn btn--ghost" data-autorizar style="margin-top:12px;">Autorizar desconto (gerente)</button>`}
<div class="modal-actions">
        <a class="btn" target="_blank" href="/orcamentos/venda/${id}/imprimir">PDF</a>
        <button class="btn btn--accent" data-imprimir>Imprimir</button>
        <button class="btn" data-close>Fechar</button>
        <button class="btn btn--ghost btn--danger" data-excluir>Excluir</button>
      </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("[data-imprimir]")!.onclick = () => {
          window.open(`/orcamentos/venda/${id}/imprimir`, "_blank");
        };
        modal.querySelector<HTMLElement>("[data-autorizar]")?.addEventListener("click", () =>
          void autorizarDescontoModal(id, () => void abrirDetalhe(id))
        );
        modal.querySelector<HTMLSelectElement>("#dStatus")!.addEventListener("change", async (e) => {
          const status = (e.target as HTMLSelectElement).value;
          try {
            await api.atualizarOrcamento(id, { status });
            toast("Status atualizado", "success");
            if (appRef) render(appRef);
          } catch (err) {
            toast("Erro: " + (err as Error).message, "error");
          }
        });
        modal.querySelector<HTMLElement>("[data-excluir]")!.onclick = async () => {
          if (!(await confirmDialog("Excluir este orçamento?"))) return;
          try {
            await api.excluirOrcamento(id);
            closeModal();
            toast("Orçamento excluído", "success");
            if (appRef) render(appRef);
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}

function autorizarDescontoModal(id: number, onOk: () => void): void {
  openModal(
    `<div class="modal-head"><h3>Autorizar desconto</h3><button class="icon-btn" data-close>×</button></div>
     <p style="font-size:13px;color:var(--ink-soft);margin:0 0 12px;">Informe as credenciais do gerente (admin ou usuário com permissão) para autorizar o desconto deste orçamento.</p>
     <div style="display:flex;flex-direction:column;gap:12px;">
       <div class="field"><label>Login do gerente</label><input id="adLogin" autocomplete="username"></div>
       <div class="field"><label>Senha</label><input id="adSenha" type="password" autocomplete="current-password"></div>
     </div>
     <div class="modal-actions">
       <button class="btn" data-close>Cancelar</button>
       <button class="btn btn--accent" id="adConfirmar">Autorizar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        const $login = modal.querySelector<HTMLInputElement>("#adLogin");
        const $senha = modal.querySelector<HTMLInputElement>("#adSenha");
        const $btn = modal.querySelector<HTMLButtonElement>("#adConfirmar")!;
        const tentar = async () => {
          const login = ($login?.value || "").trim();
          const senha = $senha?.value || "";
          if (!login || !senha) {
            toast("Informe login e senha do gerente", "error");
            return;
          }
          $btn.disabled = true;
          $btn.textContent = "Autorizando…";
          try {
            await api.autorizarDescontoOrcamento(id, { login, senha });
            toast("Desconto autorizado", "success");
            closeModal();
            onOk();
          } catch (e) {
            toast("Falha na autorização: " + (e as Error).message, "error");
            $btn.disabled = false;
            $btn.textContent = "Autorizar";
          }
        };
        $btn.addEventListener("click", () => void tentar());
        $senha?.addEventListener("keydown", (e) => { if (e.key === "Enter") void tentar(); });
        setTimeout(() => $login?.focus(), 0);
      },
    }
  );
}