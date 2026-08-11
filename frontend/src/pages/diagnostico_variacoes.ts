import { api } from "../api/client";
import { escapeHtml, fmtMoney } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

export async function render(app: HTMLElement): Promise<void> {
  app.innerHTML = `<div class="page-head"><div><h1 class="page-title">Qualidade do Catálogo</h1><p class="page-sub">Revise variantes reais, ofertas duplicadas e cadastros incompletos.</p></div></div><div id="diagResumo" class="estq-filtros"></div><div class="estq-filtros"><div class="field"><label>Buscar produto, marca, SKU ou EAN</label><input id="diagBusca" placeholder="Ex.: Cabo Flexível 750V Antichama verde"></div><select id="diagTipo"><option value="">Todos</option><option value="oferta_duplicada">Oferta duplicada</option><option value="variacao_real">Variação real</option><option value="cadastro_incompleto">Cadastro incompleto</option></select><button class="btn btn--ghost" id="diagFiltrar">Filtrar</button></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Produto</th><th>Classificação</th><th>Variantes</th><th>EANs</th><th>Observação</th><th></th></tr></thead><tbody id="diagBody"><tr><td colspan="6" class="pdv-sem-res">Carregando…</td></tr></tbody></table></div>`;
  const resumo = await api.resumoDiagnosticoVariacoes();
  app.querySelector<HTMLElement>("#diagResumo")!.innerHTML = resumo.map((r) => `<span class="badge badge--muted">${r.classificacao}: <strong>${r.produtos}</strong> produtos / ${r.variantes} variantes</span>`).join(" ");
  app.querySelector<HTMLElement>("#diagFiltrar")!.onclick = () => void carregar(app);
  await carregar(app);
}

async function carregar(app: HTMLElement): Promise<void> {
  const tipo = app.querySelector<HTMLSelectElement>("#diagTipo")?.value || undefined;
  const q = app.querySelector<HTMLInputElement>("#diagBusca")?.value.trim() || undefined;
  const body = app.querySelector<HTMLElement>("#diagBody")!;
  const rows = await api.listarDiagnosticoVariacoes({ classificacao: tipo, q, limit: 200 });
  if (!rows.length) { body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Nenhum caso</td></tr>`; return; }
  body.innerHTML = rows.map((r) => `<tr><td><strong>${escapeHtml(r.nome)}</strong><div style="font-size:11px;color:var(--ink-faint);">${escapeHtml(r.marca || "")}</div></td><td><span class="badge badge--${r.classificacao === "variacao_real" ? "ok" : r.classificacao === "oferta_duplicada" ? "muted" : "erro"}">${r.classificacao}</span></td><td>${r.n_variantes}</td><td>${r.n_eans}</td><td style="font-size:12px;">${escapeHtml(r.observacao)}</td><td><button class="btn btn--ghost btn--sm" data-detalhe="${r.produto_id}">Detalhes</button></td></tr>`).join("");
  body.querySelectorAll<HTMLElement>("[data-detalhe]").forEach((b) => b.onclick = async () => {
    const d = await api.detalhesDiagnosticoVariacao(Number(b.dataset.detalhe));
    const produtoId = Number(b.dataset.detalhe);
    openModal(
      `<div class="modal-head"><h3>${escapeHtml(d.produto?.nome || "Produto")}</h3><button class="icon-btn" data-close>×</button></div>
       <p style="font-size:13px;color:var(--ink-soft);">Escolha a variante principal. As demais ofertas com o mesmo EAN serão desativadas, mantendo histórico e referências.</p>
       <div class="table-wrap"><table class="data-table"><thead><tr><th>ID</th><th>SKU</th><th>EAN</th><th>Preço</th><th></th></tr></thead><tbody>
       ${d.variantes.map((v) => `<tr><td>${v.id}</td><td>${escapeHtml(v.sku || "—")}</td><td>${escapeHtml(v.ean || "—")}</td><td>${fmtMoney(v.preco)}</td><td><button class="btn btn--accent btn--sm" data-principal="${v.id}">Usar como principal</button></td></tr>`).join("")}
       </tbody></table></div>
       <div class="modal-actions"><button class="btn" data-close>Fechar</button></div>`,
      { onMount: (m) => {
        m.querySelectorAll("[data-close]").forEach((el) => ((el as HTMLElement).onclick = closeModal));
        m.querySelectorAll<HTMLElement>("[data-principal]").forEach((button) => {
          button.onclick = async () => {
            if (!confirm("Confirmar consolidação das ofertas neste produto?")) return;
            try {
              const result = await api.consolidarOfertas(produtoId, Number(button.dataset.principal));
              toast(`${result.desativadas} ofertas consolidadas`, "success");
              closeModal();
              await carregar(app);
            } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
          };
        });
      } }
    );
  });
}
