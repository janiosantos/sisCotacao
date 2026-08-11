import "../styles/estoque.css";
import { api, type TabelaPreco, type TabelaPrecoPayload } from "../api/client";
import type { Promocao, PromocaoPayload } from "../api/client";
import { escapeHtml, fmtDate, fmtMoney } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

let currentApp: HTMLElement | null = null;
let abaAtiva = "tabelas";

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  paint();
  await carregarAba();
}

function paint(): void {
  if (!currentApp) return;
  currentApp.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Preços</h1>
      <p class="page-sub">Tabelas de preço e promoções.</p>
    </div>
    <div class="tab-bar">
      <button class="tab-btn ${abaAtiva === "tabelas" ? "is-active" : ""}" data-aba="tabelas">Tabelas</button>
      <button class="tab-btn ${abaAtiva === "promocoes" ? "is-active" : ""}" data-aba="promocoes">Promoções</button>
      <button class="tab-btn ${abaAtiva === "revisoes" ? "is-active" : ""}" data-aba="revisoes">Revisões</button>
    </div>
    <div id="precContent" class="estq-content"></div>
  `;
  currentApp.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      abaAtiva = btn.dataset.aba || "tabelas";
      paint();
      void carregarAba();
    });
  });
}

async function carregarAba(): Promise<void> {
  const $ct = currentApp?.querySelector<HTMLElement>("#precContent");
  if (!$ct) return;
  if (abaAtiva === "tabelas") await renderTabelas($ct);
  else if (abaAtiva === "promocoes") await renderPromocoes($ct);
  else if (abaAtiva === "revisoes") await renderRevisoes($ct);
}

// ──────────────────────────────────────────────────────────
//  Tabelas de Preço
// ──────────────────────────────────────────────────────────

async function renderTabelas($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaTab">Nova tabela</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Nome</th><th>Tipo</th><th>Margem</th><th>Markup</th><th>Status</th><th></th></tr></thead>
      <tbody id="tblTabBody"><tr><td colspan="6" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaTab")!.addEventListener("click", () => abrirModalTabela(null));
  await carregarTabelas();
}

async function carregarTabelas(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblTabBody");
  if (!$body) return;
  try {
    const res = await api.listarTabelasPreco();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Nenhuma tabela</td></tr>`; return; }
    $body.innerHTML = res.map((t) => `
      <tr>
        <td><strong>${escapeHtml(t.nome)}</strong></td>
        <td><span class="badge badge--muted">${t.tipo}</span></td>
        <td>${t.margem_padrao ? t.margem_padrao + "%" : "—"}</td>
        <td>${t.markup ? t.markup + "%" : "—"}</td>
        <td><span class="badge badge--${t.ativo ? "ok" : "muted"}">${t.ativo ? "Ativo" : "Inativo"}</span></td>
        <td class="cell-actions">
          <button class="btn btn--ghost btn--sm" data-itens="${t.id}">Itens</button>
          <button class="btn btn--ghost btn--sm" data-gerar="${t.id}">Gerar</button>
          <button class="btn btn--ghost btn--sm" data-editar="${t.id}">Editar</button>
          <button class="btn btn--ghost btn--sm" data-toggle="${t.id}">${t.ativo ? "Desat." : "Ativar"}</button>
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-editar]").forEach((b) => {
      b.addEventListener("click", () => {
        const t = res.find((x) => x.id === Number(b.dataset.editar));
        if (t) abrirModalTabela(t);
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
      b.addEventListener("click", async () => {
        const t = res.find((x) => x.id === Number(b.dataset.toggle));
        if (t) { await api.alternarAtivoTabelaPreco(t.id, !t.ativo); await carregarTabelas(); }
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-itens]").forEach((b) => {
      b.addEventListener("click", () => {
        const t = res.find((x) => x.id === Number(b.dataset.itens));
        if (t) abrirModalItensTabela(t);
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-gerar]").forEach((b) => {
      b.addEventListener("click", () => {
        const t = res.find((x) => x.id === Number(b.dataset.gerar));
        if (t) abrirModalGerarPrecos(t);
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="6" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalTabela(tab: TabelaPreco | null): void {
  const editando = !!tab;
  const tipos = ["varejo", "atacado", "contrato", "promocional"];
  const opts = tipos.map((t) => `<option value="${t}" ${tab?.tipo === t ? "selected" : ""}>${t}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>${editando ? "Editar" : "Nova"} tabela</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Nome</label><input id="tNome" value="${escapeHtml(tab?.nome || "")}" autocomplete="off"></div>
       <div class="field"><label>Tipo</label><select id="tTipo">${opts}</select></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Margem % (custo)</label><input id="tMargem" type="number" step="0.1" value="${tab?.margem_padrao || 0}"></div>
         <div class="field" style="flex:1"><label>Markup % (custo)</label><input id="tMarkup" type="number" step="0.1" value="${tab?.markup || 0}"></div>
       </div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="tSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#tSalvar")!.onclick = async () => {
          const payload: TabelaPrecoPayload = {
            nome: (m.querySelector<HTMLInputElement>("#tNome")?.value || "").trim(),
            tipo: m.querySelector<HTMLSelectElement>("#tTipo")?.value || "varejo",
            margem_padrao: parseFloat((m.querySelector<HTMLInputElement>("#tMargem")?.value || "0").replace(",", ".")),
            markup: parseFloat((m.querySelector<HTMLInputElement>("#tMarkup")?.value || "0").replace(",", ".")),
          };
          if (!payload.nome) { toast("Informe o nome", "error"); return; }
          try {
            if (editando) await api.atualizarTabelaPreco(tab!.id, payload);
            else await api.criarTabelaPreco(payload);
            toast(editando ? "Tabela atualizada" : "Tabela criada", "success");
            closeModal();
            await carregarTabelas();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

function abrirModalItensTabela(tab: TabelaPreco): void {
  let termo = "";
  openModal(
    `<div class="modal-head"><h3>${escapeHtml(tab.nome)} — Itens</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field" style="margin-bottom:10px;">
       <input id="tiBusca" placeholder="Buscar produto…" autocomplete="off">
     </div>
     <div class="table-wrap" style="max-height:360px;overflow:auto;">
       <table class="data-table"><thead><tr><th>Produto</th><th>SKU</th><th>Preço</th><th>Custo</th><th>Margem %</th></tr></thead>
       <tbody id="tiBody"><tr><td colspan="5" class="pdv-sem-res">Carregando…</td></tr></tbody>
     </table></div>
     <div class="modal-actions"><button class="btn" data-close>Fechar</button></div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        const $busca = m.querySelector<HTMLInputElement>("#tiBusca")!;
        const carregar = async () => {
          try {
            const itens = await api.listarItensTabelaMargem(tab.id, termo || undefined);
            const $body = m.querySelector<HTMLElement>("#tiBody")!;
            if (!itens.length) { $body.innerHTML = `<tr><td colspan="5" class="pdv-sem-res">Nenhum item</td></tr>`; return; }
            $body.innerHTML = itens.map((i) => `
              <tr>
                <td><strong>${escapeHtml(i.produto_nome)}</strong>${i.marca ? `<div style="font-size:11px;color:var(--ink-faint);">${escapeHtml(i.marca)}</div>` : ""}</td>
                <td style="font-size:12px;font-family:var(--font-mono);">${escapeHtml(i.sku)}</td>
                <td>${fmtMoney(i.preco)}</td>
                <td>${i.custo_unitario ? fmtMoney(i.custo_unitario) : "—"}</td>
                <td><strong>${i.margem_pct != null ? i.margem_pct.toFixed(1) + "%" : "—"}</strong></td>
              </tr>`).join("");
          } catch { /* silêncio */ }
        };
        $busca.addEventListener("input", () => {
          termo = $busca.value.trim();
          void carregar();
        });
        void carregar();
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Revisões
// ──────────────────────────────────────────────────────────

async function renderRevisoes($ct: HTMLElement): Promise<void> {
  let tabelas: TabelaPreco[] = [];
  try { tabelas = await api.listarTabelasPreco(); } catch { /* */ }
  const opts = tabelas.map((t) => `<option value="${t.id}">${escapeHtml(t.nome)}</option>`).join("");
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaRev">Nova revisão</button></p>
    <div class="estq-filtros">
      <div class="field"><label>Tabela</label>
        <select id="filtroRevTab"><option value="">Todas</option>${opts}</select>
      </div>
      <button class="btn btn--ghost" id="btnFiltrarRev">Filtrar</button>
    </div>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Código</th><th>Descrição</th><th>Tabela</th><th>Cliente</th><th>Data</th><th>Validade</th><th>Situação</th><th></th></tr></thead>
      <tbody id="tblRevBody"><tr><td colspan="8" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaRev")!.addEventListener("click", async () => {
    const tabs = await api.listarTabelasPreco();
    abrirModalCriarRevisao(tabs);
  });
  $ct.querySelector<HTMLElement>("#btnFiltrarRev")!.addEventListener("click", () => void carregarRevisoes());
  await carregarRevisoes();
}

async function carregarRevisoes(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblRevBody");
  if (!$body) return;
  const tabela_id = parseInt(currentApp?.querySelector<HTMLSelectElement>("#filtroRevTab")?.value || "", 10) || undefined;
  try {
    const res = await api.listarRevisoesPreco(tabela_id);
    if (!res.length) { $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Nenhuma revisão</td></tr>`; return; }
    $body.innerHTML = res.map((r) => `
      <tr>
        <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(r.codigo)}</td>
        <td>${escapeHtml(r.descricao)}</td>
        <td>${escapeHtml(r.tabela_nome)}</td>
        <td>${r.cliente_nome ? escapeHtml(r.cliente_nome) : "—"}</td>
        <td style="font-size:12px;color:var(--ink-soft);">${fmtDate(r.data_cadastro)}</td>
        <td style="font-size:12px;color:var(--ink-soft);">${r.data_validade ? fmtDate(r.data_validade) : "—"}</td>
        <td><span class="badge badge--${r.situacao === "aberta" ? "muted" : "ok"}">${r.situacao}</span></td>
        <td class="cell-actions">
          ${r.situacao === "aberta" ? `<button class="btn btn--sm btn--ghost" data-fechar="${r.id}">Fechar</button>` : ""}
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-fechar]").forEach((b) => {
      b.addEventListener("click", async () => {
        try {
          await api.fecharRevisaoPreco(Number(b.dataset.fechar));
          toast("Revisão fechada", "success");
          await carregarRevisoes();
        } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
      });
    });
  } catch { $body.innerHTML = `<tr><td colspan="8" class="pdv-sem-res">Erro</td></tr>`; }
}

async function abrirModalCriarRevisao(tabelas: TabelaPreco[]): Promise<void> {
  const opts = tabelas.map((t) => `<option value="${t.id}">${escapeHtml(t.nome)}</option>`).join("");
  openModal(
    `<div class="modal-head"><h3>Nova revisão</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Tabela</label><select id="rvTabela">${opts}</select></div>
       <div class="field"><label>Código</label><input id="rvCodigo" placeholder="Ex.: REV-001"></div>
       <div class="field"><label>Descrição</label><input id="rvDesc" placeholder="Ex.: Preços Iniciais"></div>
       <div class="field"><label>Cliente (ID, opcional)</label><input id="rvCliente" type="number" min="1" placeholder="ID do cliente"></div>
       <div class="field"><label>Data validade (opcional)</label><input id="rvValidade" type="date"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="rvSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#rvSalvar")!.onclick = async () => {
          try {
            await api.criarRevisaoPreco({
              tabela_id: parseInt(m.querySelector<HTMLSelectElement>("#rvTabela")?.value || "0", 10),
              codigo: (m.querySelector<HTMLInputElement>("#rvCodigo")?.value || "").trim(),
              descricao: (m.querySelector<HTMLInputElement>("#rvDesc")?.value || "").trim() || undefined,
              cliente_id: parseInt(m.querySelector<HTMLInputElement>("#rvCliente")?.value || "", 10) || undefined,
              data_validade: m.querySelector<HTMLInputElement>("#rvValidade")?.value || undefined,
            });
            toast("Revisão criada", "success");
            closeModal();
            await carregarRevisoes();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

function abrirModalGerarPrecos(tab: TabelaPreco): void {
  openModal(
    `<div class="modal-head"><h3>Gerar preços — ${escapeHtml(tab.nome)}</h3><button class="icon-btn" data-close>×</button></div>
     <p style="font-size:13px;color:var(--ink-soft);margin-bottom:14px;">
       Gera automaticamente os preços com base no custo unitário das variantes que têm custo cadastrado.
     </p>
     <div class="field-row">
       <div class="field" style="flex:1"><label>Margem % (preço = custo ÷ (1 − margem))</label>
         <input id="gpMargem" type="number" step="0.1" value="${tab.margem_padrao || 0}"></div>
       <div class="field" style="flex:1"><label>Markup % (preço = custo × (1 + markup))</label>
         <input id="gpMarkup" type="number" step="0.1" value="${tab.markup || 0}"></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="gpGerar">Gerar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#gpGerar")!.onclick = async () => {
          const margem = parseFloat((m.querySelector<HTMLInputElement>("#gpMargem")?.value || "").replace(",", "."));
          const markup = parseFloat((m.querySelector<HTMLInputElement>("#gpMarkup")?.value || "").replace(",", "."));
          try {
            const res = await api.gerarPrecosTabela(tab.id, {
              ...(isNaN(margem) ? {} : { margem }),
              ...(isNaN(markup) ? {} : { markup }),
            });
            toast(`${res.gerados} preços gerados`, "success");
            closeModal();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Promoções
// ──────────────────────────────────────────────────────────

async function renderPromocoes($ct: HTMLElement): Promise<void> {
  $ct.innerHTML = `
    <p><button class="btn btn--accent" id="btnNovaPromo">Nova promoção</button></p>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Nome</th><th>Tipo</th><th>Valor</th><th>Início</th><th>Fim</th><th>Status</th><th></th></tr></thead>
      <tbody id="tblPromoBody"><tr><td colspan="7" class="pdv-sem-res">Carregando…</td></tr></tbody>
    </table></div>
  `;
  $ct.querySelector<HTMLElement>("#btnNovaPromo")!.addEventListener("click", () => abrirModalPromocao(null));
  await carregarPromocoes();
}

async function carregarPromocoes(): Promise<void> {
  const $body = currentApp?.querySelector<HTMLElement>("#tblPromoBody");
  if (!$body) return;
  try {
    const res = await api.listarPromocoes();
    if (!res.length) { $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Nenhuma promoção</td></tr>`; return; }
    $body.innerHTML = res.map((p) => `
      <tr>
        <td><strong>${escapeHtml(p.nome)}</strong></td>
        <td><span class="badge badge--muted">${p.tipo === "percentual" ? "%" : "R$"}</span></td>
        <td>${p.tipo === "percentual" ? p.valor + "%" : fmtMoney(p.valor)}</td>
        <td style="font-size:12px;color:var(--ink-soft);">${p.data_inicio ? fmtDate(p.data_inicio) : "—"}</td>
        <td style="font-size:12px;color:var(--ink-soft);">${p.data_fim ? fmtDate(p.data_fim) : "—"}</td>
        <td><span class="badge badge--${p.ativo ? "ok" : "muted"}">${p.ativo ? "Ativa" : "Inativa"}</span></td>
        <td class="cell-actions">
          <button class="btn btn--ghost btn--sm" data-aplicar="${p.id}">Aplicar</button>
          <button class="btn btn--ghost btn--sm" data-itens="${p.id}">Itens</button>
          <button class="btn btn--ghost btn--sm" data-editar="${p.id}">Editar</button>
          <button class="btn btn--ghost btn--sm" data-toggle="${p.id}">${p.ativo ? "Desat." : "Ativar"}</button>
        </td>
      </tr>`).join("");
    $body.querySelectorAll<HTMLElement>("[data-editar]").forEach((b) => {
      b.addEventListener("click", () => {
        const p = res.find((x) => x.id === Number(b.dataset.editar));
        if (p) abrirModalPromocao(p);
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
      b.addEventListener("click", async () => {
        const p = res.find((x) => x.id === Number(b.dataset.toggle));
        if (p) { await api.atualizarPromocao(p.id, { nome: p.nome, tipo: p.tipo, valor: p.valor, data_inicio: p.data_inicio ?? undefined, data_fim: p.data_fim ?? undefined, ativo: p.ativo ? 0 : 1 }); await carregarPromocoes(); }
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-itens]").forEach((b) => {
      b.addEventListener("click", () => {
        const p = res.find((x) => x.id === Number(b.dataset.itens));
        if (p) abrirModalItensPromocao(p);
      });
    });
    $body.querySelectorAll<HTMLElement>("[data-aplicar]").forEach((b) => {
      b.addEventListener("click", () => {
        const p = res.find((x) => x.id === Number(b.dataset.aplicar));
        if (p) abrirModalAplicarPromocao(p);
      });
    });
  } catch {
    $body.innerHTML = `<tr><td colspan="7" class="pdv-sem-res">Erro</td></tr>`;
  }
}

function abrirModalPromocao(p: Promocao | null): void {
  const editando = !!p;
  openModal(
    `<div class="modal-head"><h3>${editando ? "Editar" : "Nova"} promoção</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Nome</label><input id="pNome" value="${escapeHtml(p?.nome || "")}" autocomplete="off"></div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Tipo</label>
           <select id="pTipo"><option value="percentual" ${p?.tipo === "percentual" ? "selected" : ""}>Percentual (%)</option><option value="valor_fixo" ${p?.tipo === "valor_fixo" ? "selected" : ""}>Valor fixo (R$)</option></select>
         </div>
         <div class="field" style="flex:1"><label>Valor</label><input id="pValor" type="number" step="0.01" value="${p?.valor || 0}"></div>
       </div>
       <div class="field-row">
         <div class="field" style="flex:1"><label>Início</label><input id="pInicio" type="date" value="${p?.data_inicio || ""}"></div>
         <div class="field" style="flex:1"><label>Fim</label><input id="pFim" type="date" value="${p?.data_fim || ""}"></div>
       </div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="pSalvar">Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#pSalvar")!.onclick = async () => {
          const payload: PromocaoPayload = {
            nome: (m.querySelector<HTMLInputElement>("#pNome")?.value || "").trim(),
            tipo: m.querySelector<HTMLSelectElement>("#pTipo")?.value || "percentual",
            valor: parseFloat((m.querySelector<HTMLInputElement>("#pValor")?.value || "0").replace(",", ".")),
            data_inicio: m.querySelector<HTMLInputElement>("#pInicio")?.value || undefined,
            data_fim: m.querySelector<HTMLInputElement>("#pFim")?.value || undefined,
          };
          if (!payload.nome) { toast("Informe o nome", "error"); return; }
          try {
            if (editando) await api.atualizarPromocao(p!.id, payload);
            else await api.criarPromocao(payload);
            toast(editando ? "Promoção atualizada" : "Promoção criada", "success");
            closeModal();
            await carregarPromocoes();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}

function abrirModalItensPromocao(p: Promocao): void {
  let termo = "";
  openModal(
    `<div class="modal-head"><h3>${escapeHtml(p.nome)} — Itens</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field" style="margin-bottom:10px;">
       <input id="piBusca" placeholder="Buscar produto…" autocomplete="off">
     </div>
     <div class="table-wrap" style="max-height:360px;overflow:auto;">
       <table class="data-table"><thead><tr><th>Produto</th><th>SKU</th><th>Preço base</th><th>Preço promocional</th></tr></thead>
       <tbody id="piBody"><tr><td colspan="4" class="pdv-sem-res">Carregando…</td></tr></tbody>
     </table></div>
     <div class="modal-actions"><button class="btn" data-close>Fechar</button></div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        const $busca = m.querySelector<HTMLInputElement>("#piBusca")!;
        const carregar = async () => {
          try {
            const itens = await api.listarItensPromocao(p.id, termo || undefined);
            const $body = m.querySelector<HTMLElement>("#piBody")!;
            if (!itens.length) { $body.innerHTML = `<tr><td colspan="4" class="pdv-sem-res">Nenhum item</td></tr>`; return; }
            $body.innerHTML = itens.map((i) => `
              <tr>
                <td><strong>${escapeHtml(i.produto_nome)}</strong></td>
                <td style="font-size:12px;font-family:var(--font-mono);">${escapeHtml(i.sku)}</td>
                <td>${fmtMoney(i.preco_base)}</td>
                <td><strong>${fmtMoney(i.preco_promocional)}</strong></td>
              </tr>`).join("");
          } catch { /* silêncio */ }
        };
        $busca.addEventListener("input", () => { termo = $busca.value.trim(); void carregar(); });
        void carregar();
      },
    }
  );
}

function abrirModalAplicarPromocao(p: Promocao): void {
  openModal(
    `<div class="modal-head"><h3>Aplicar — ${escapeHtml(p.nome)}</h3><button class="icon-btn" data-close>×</button></div>
     <p style="font-size:13px;color:var(--ink-soft);margin-bottom:14px;">
       Aplica a promoção a produtos por ID da variante. Informe os IDs separados por vírgula.
       ${p.tipo === "percentual" ? `Desconto de <strong>${p.valor}%</strong> sobre o preço base.` : `Preço fixo de <strong>${fmtMoney(p.valor)}</strong>.`}
     </p>
     <div class="field"><label>IDs das variantes (separados por vírgula)</label>
       <textarea id="apIds" rows="3" placeholder="Ex.: 1, 2, 3, 10, 15"></textarea>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" id="apAplicar">Aplicar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(m) {
        m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        m.querySelector<HTMLElement>("#apAplicar")!.onclick = async () => {
          const texto = (m.querySelector<HTMLInputElement>("#apIds")?.value || "").trim();
          if (!texto) { toast("Informe ao menos um ID", "error"); return; }
          const ids = texto.split(",").map((s) => parseInt(s.trim(), 10)).filter((n) => !isNaN(n) && n > 0);
          if (!ids.length) { toast("IDs inválidos", "error"); return; }
          try {
            const res = await api.aplicarPromocao(p.id, ids);
            toast(`${res.aplicados} itens aplicados`, "success");
            closeModal();
          } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
        };
      },
    }
  );
}
