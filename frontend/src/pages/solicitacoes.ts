import { api } from "../api/client";
import { escapeHtml, fmtDate } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando…</div>`;
  $app.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Solicitações de Compra</h1>
      <p class="page-sub">Solicitações internas com aprovação.</p>
      <button class="btn btn--accent" id="btnNovaSol">Nova solicitação</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Código</th><th>Descrição</th><th>Data</th><th>Solicitante</th><th>Status</th></tr></thead>
      <tbody id="tblSolBody"><tr><td colspan="5" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>`;
  $app.querySelector<HTMLElement>("#btnNovaSol")!.addEventListener("click", () => abrirModalSolicitacao());
  await carregar();
}

async function carregar(): Promise<void> {
  const $body = document.querySelector<HTMLElement>("#tblSolBody");
  if (!$body) return;
  try {
    const r = await api.listarSolicitacoesCompra();
    if (!r.length) { $body.innerHTML = `<tr><td colspan="5" class="pdv-sem-res">Nenhuma solicitação</td></tr>`; return; }
    $body.innerHTML = r.map((s) => `
      <tr>
        <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(s.codigo)}</td>
        <td>${escapeHtml(s.descricao)}</td>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(s.data_solicitacao)}</td>
        <td>${escapeHtml(s.usuario_nome || "—")}</td>
        <td><span class="badge badge--${s.status === "aprovada" ? "ok" : s.status === "rejeitada" ? "cancelada" : "rascunho"}">${s.status}</span></td>
      </tr>`).join("");
  } catch { $body.innerHTML = `<tr><td colspan="5" class="pdv-sem-res">Erro</td></tr>`; }
}

function abrirModalSolicitacao(): void {
  openModal(
    `<div class="modal-head"><h3>Nova solicitação</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Código</label><input id="solCodigo" placeholder="SOL-001"></div>
       <div class="field"><label>Descrição</label><textarea id="solDesc" rows="3"></textarea></div>
       <div class="field"><label>Observação</label><textarea id="solObs" rows="2"></textarea></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="solSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    { onMount(m) {
      m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
      m.querySelector<HTMLElement>("#solSalvar")!.onclick = async () => {
        try {
          await api.criarSolicitacaoCompra({
            codigo: (m.querySelector<HTMLInputElement>("#solCodigo")?.value || "").trim(),
            descricao: (m.querySelector<HTMLInputElement>("#solDesc")?.value || "").trim() || undefined,
            observacao: (m.querySelector<HTMLInputElement>("#solObs")?.value || "").trim() || undefined,
          });
          toast("Solicitação criada", "success"); closeModal(); location.reload();
        } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
      };
    }}
  );
}
