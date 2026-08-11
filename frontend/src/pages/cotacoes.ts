// pages/cotacoes.ts — lista de cotações e tela de comparação/fechamento.

import {
  api,
  type CotacaoDetalhe,
  type CotacaoFornecedor,
  type CotacaoLista,
  type Fornecedor,
  type ItemCotacao,
  type Preco,
  type ProdutoResumo,
  type Vencedor,
} from "../api/client";
import { escapeHtml, fmtDate, fmtDateTime, fmtMoney } from "../ui/format";
import { closeModal, confirmDialog, openModal, toast } from "../ui/dom";
import { abrir as abrirImportia } from "./importia";

let currentFilter = "";

const STATUS_LABELS: Record<string, string> = {
  aberta: "Aberta",
  fechada: "Fechada",
  cancelada: "Cancelada",
  pendente: "Pendente",
  analise: "Pronta para Analisar",
  finalizada: "Finalizada",
  respondido: "Respondido",
};

function statusLabel(status: string): string {
  return STATUS_LABELS[status] || status;
}

// ------------------------------------------------------------
// LISTA
// ------------------------------------------------------------

export async function renderLista($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando cotações…</div>`;
  let cotacoes: CotacaoLista[] = [];
  try {
    cotacoes = await api.listarCotacoes(currentFilter);
  } catch (e) {
    toast("Erro ao carregar cotações: " + (e as Error).message, "error");
  }

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Cotações</h1>
        <p class="page-sub">Solicitações de preço enviadas a fornecedores.</p>
      </div>
      <a class="btn btn--accent" href="#/catalogo">+ Nova cotação</a>
    </div>

    <div class="toolbar">
      <div class="field">
        <label>Status</label>
        <select id="fStatus">
          <option value="">Todas</option>
          <option value="pendente">Pendente</option>
          <option value="analise">Pronta para Analisar</option>
          <option value="finalizada">Finalizada</option>
          <option value="aberta">Abertas</option>
          <option value="fechada">Fechadas</option>
          <option value="cancelada">Canceladas</option>
        </select>
      </div>
      <span class="result-count">${cotacoes.length} cotações</span>
    </div>

    ${cotacoes.length === 0 ? emptyList() : listTable(cotacoes)}
  `;

  $app.querySelector<HTMLSelectElement>("#fStatus")!.value = currentFilter;
  $app.querySelector<HTMLSelectElement>("#fStatus")!.addEventListener("change", (e) => {
    currentFilter = (e.target as HTMLSelectElement).value;
    renderLista($app);
  });
  $app.querySelectorAll<HTMLElement>("tr[data-id]").forEach((tr) => {
    tr.addEventListener("click", () => (location.hash = `#/cotacoes/${tr.dataset.id}`));
  });
  $app.querySelectorAll<HTMLElement>("[data-abrir-comprar]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      sessionStorage.setItem("compras_cotacao", String(btn.dataset.abrirComprar));
      location.hash = "#/compras";
    });
  });
}

function emptyList(): string {
  return `<div class="empty-box"><p>Nenhuma cotação ainda</p><p>Vá até o Catálogo, selecione produtos e crie sua primeira cotação.</p></div>`;
}

function listTable(cotacoes: CotacaoLista[]): string {
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>Nº</th><th>Título</th><th>Cliente</th><th>Status</th><th>Itens</th><th>Respostas</th><th>Criada em</th><th></th>
        </tr></thead>
        <tbody>
          ${cotacoes
            .map(
              (c) => `
              <tr data-id="${c.id}" class="row-link">
                <td style="font-family:var(--font-mono);">${c.numero}</td>
                <td>${escapeHtml(c.titulo || "—")}</td>
                <td>${escapeHtml(c.cliente || "—")}</td>
                <td><span class="badge badge--${c.status}">${statusLabel(c.status)}</span></td>
                <td>${c.n_itens}</td>
                <td>${c.n_respostas} / ${c.n_fornecedores}</td>
                <td>${fmtDate(c.criado_em)}</td>
                <td>${
                  c.status === "pendente" || c.status === "analise" || c.status === "finalizada"
                    ? `<button class="btn btn--sm" data-abrir-comprar="${c.id}">Abrir no Comprar</button>`
                    : ""
                }</td>
              </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
}

// ------------------------------------------------------------
// DETALHE / COMPARAÇÃO
// ------------------------------------------------------------

export async function renderDetalhe($app: HTMLElement, cotacaoId: number): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando cotação…</div>`;
  let data: CotacaoDetalhe;
  let todosFornecedores: Fornecedor[];
  try {
    [data, todosFornecedores] = await Promise.all([
      api.detalharCotacao(cotacaoId),
      api.listarFornecedores(true),
    ]);
  } catch (e) {
    $app.innerHTML = `<div class="empty-box"><p>Erro</p><p>${escapeHtml((e as Error).message)}</p></div>`;
    return;
  }
  const { cotacao, itens, fornecedores, precos, vencedores } = data;

  const precoMap: Record<string, Preco> = {};
  for (const p of precos) precoMap[`${p.cotacao_item_id}:${p.fornecedor_id}`] = p;
  const vencedorMap: Record<number, Vencedor> = {};
  for (const v of vencedores) vencedorMap[v.cotacao_item_id] = v;

  const isFechada = cotacao.status === "fechada";

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <a href="#/cotacoes" style="font-size:12.5px;color:var(--ink-soft);">← Todas as cotações</a>
        <h1 class="page-title" style="margin-top:6px;">Cotação nº ${cotacao.numero}</h1>
        <p class="page-sub">${escapeHtml(cotacao.titulo || "Sem título")} · criada em ${fmtDateTime(cotacao.criado_em)}${
          cotacao.cliente ? " · cliente " + escapeHtml(cotacao.cliente) : ""
        }</p>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <span class="badge badge--${cotacao.status}">${statusLabel(cotacao.status)}</span>
        <a class="btn btn--sm" href="/orcamentos/${cotacao.id}/imprimir" target="_blank">Imprimir</a>
        <button class="btn btn--ghost btn--sm" id="btnEditar">Editar</button>
        ${
          isFechada
            ? `<button class="btn btn--sm" id="btnReabrir">Reabrir</button>`
            : `<button class="btn btn--accent btn--sm" id="btnFechar">Fechar cotação</button>`
        }
      </div>
    </div>

    ${cotacao.observacoes ? `<p style="font-size:13px;color:var(--ink-soft);margin:-8px 0 18px;">Obs.: ${escapeHtml(cotacao.observacoes)}</p>` : ""}

    <div style="display:flex;justify-content:space-between;align-items:center;margin:18px 0 8px;flex-wrap:wrap;gap:10px;">
      <h3 style="font-size:15px;">Comparação de preços</h3>
      ${isFechada ? "" : `
        <div style="display:flex;gap:8px;">
          <button class="btn btn--sm" id="btnImportarIA">⚡ Importar retorno</button>
          <button class="btn btn--sm" id="btnAddFornecedor">+ Fornecedor</button>
          <button class="btn btn--sm" id="btnAddItem">+ Item</button>
        </div>`}
    </div>

    <div id="compareWrap"></div>
    <div id="summaryWrap"></div>
  `;

  renderCompareTable($app, { cotacaoId, itens, fornecedores, precoMap, vencedorMap, isFechada });

  $app.querySelector<HTMLButtonElement>("#btnEditar")!.addEventListener("click", () =>
    abrirModalEditarCotacao($app, cotacao)
  );
  if (isFechada) {
    $app.querySelector<HTMLButtonElement>("#btnReabrir")!.addEventListener("click", async () => {
      if (!(await confirmDialog("Reabrir esta cotação para novos lançamentos de preço?"))) return;
      await api.reabrirCotacao(cotacaoId);
      renderDetalhe($app, cotacaoId);
    });
    renderSummary($app, { itens, vencedores, fornecedores });
  } else {
    $app.querySelector<HTMLButtonElement>("#btnFechar")!.addEventListener("click", () =>
      abrirModalFechar($app, { cotacaoId, itens, fornecedores, precoMap })
    );
    $app.querySelector<HTMLButtonElement>("#btnImportarIA")!.addEventListener("click", () => {
      abrirImportia({
        cotacaoId,
        fornecedores,
        titulo: "Cotação nº " + cotacao.numero,
        onAplicado: () => renderDetalhe($app, cotacaoId),
      });
    });
    $app.querySelector<HTMLButtonElement>("#btnAddFornecedor")!.addEventListener("click", () =>
      abrirModalAddFornecedor($app, cotacaoId, fornecedores, todosFornecedores)
    );
    $app.querySelector<HTMLButtonElement>("#btnAddItem")!.addEventListener("click", () =>
      abrirModalAddItem($app, cotacaoId)
    );
  }
}

function renderCompareTable(
  $app: HTMLElement,
  {
    cotacaoId,
    itens,
    fornecedores,
    precoMap,
    vencedorMap,
    isFechada,
  }: {
    cotacaoId: number;
    itens: ItemCotacao[];
    fornecedores: CotacaoFornecedor[];
    precoMap: Record<string, Preco>;
    vencedorMap: Record<number, Vencedor>;
    isFechada: boolean;
  }
): void {
  const $wrap = $app.querySelector<HTMLElement>("#compareWrap")!;
  if (itens.length === 0) {
    $wrap.innerHTML = `<div class="empty-box"><p>Sem itens</p><p>Adicione produtos a esta cotação.</p></div>`;
    return;
  }
  if (fornecedores.length === 0) {
    $wrap.innerHTML = `<div class="empty-box"><p>Sem fornecedores convidados</p><p>Adicione ao menos um fornecedor para lançar preços.</p></div>`;
    return;
  }

  $wrap.innerHTML = `
    <div class="compare-wrap">
      <table class="compare-table">
        <thead>
          <tr>
            <th style="min-width:220px;">Produto</th>
            <th class="qty-col">Qtd.</th>
            ${fornecedores
              .map(
                (f) => `<th>${escapeHtml(f.nome)}<br><span class="badge badge--${f.status}" style="margin-top:4px;">${statusLabel(f.status)}</span></th>`
              )
              .join("")}
          </tr>
        </thead>
        <tbody>
          ${itens.map((it) => rowHtml(it, fornecedores, precoMap, vencedorMap, isFechada)).join("")}
        </tbody>
      </table>
    </div>`;

  if (!isFechada) {
    $wrap.querySelectorAll<HTMLInputElement>(".price-input").forEach((input) => {
      input.addEventListener("change", async (e) => {
        const target = e.target as HTMLInputElement;
        const val = parseFloat(target.value.replace(",", "."));
        const itemId = Number(target.dataset.item);
        const fornecedorId = Number(target.dataset.fornecedor);
        if (isNaN(val) || val < 0) {
          toast("Preço inválido", "error");
          return;
        }
        try {
          await api.registrarPreco(cotacaoId, {
            cotacao_item_id: itemId,
            fornecedor_id: fornecedorId,
            preco_unitario: val,
          });
          toast("Preço registrado", "success");
          renderDetalhe($app, cotacaoId);
        } catch (err) {
          toast("Erro: " + (err as Error).message, "error");
        }
      });
    });
    $wrap.querySelectorAll<HTMLButtonElement>(".btn-remove-item").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!(await confirmDialog("Remover este item da cotação?"))) return;
        await api.removerItem(cotacaoId, Number(btn.dataset.item));
        renderDetalhe($app, cotacaoId);
      });
    });
  }
}

function rowHtml(
  it: ItemCotacao,
  fornecedores: CotacaoFornecedor[],
  precoMap: Record<string, Preco>,
  vencedorMap: Record<number, Vencedor>,
  isFechada: boolean
): string {
  const rowPrecos = fornecedores
    .map((f) => precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`])
    .filter(Boolean);
  const best = rowPrecos.length ? Math.min(...rowPrecos.map((p) => p.preco_unitario)) : null;
  const vencedor = vencedorMap[it.cotacao_item_id];

  return `
    <tr>
      <td>
        <div class="compare-item-cell">
          ${it.imagem_url ? `<img src="${escapeHtml(it.imagem_url)}" alt="">` : `<span style="width:34px;"></span>`}
          <div>
            <div class="compare-item-code">${escapeHtml(it.sku || "#" + it.produto_id)}</div>
            <div class="compare-item-desc">${escapeHtml(it.name)}</div>
          </div>
          ${
            isFechada
              ? ""
              : `<button class="icon-btn btn-remove-item" data-item="${it.cotacao_item_id}" style="margin-left:auto;" title="Remover item">×</button>`
          }
        </div>
      </td>
      <td class="qty-col">${it.quantidade}</td>
      ${fornecedores
        .map((f) => {
          const p = precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`];
          const isBest = p != null && best !== null && p.preco_unitario === best;
          const isWinner = vencedor && vencedor.fornecedor_id === f.fornecedor_id;
          const delta = p != null && best !== null && !isBest ? (((p.preco_unitario - best) / best) * 100).toFixed(1) : null;
          const pack = p && p.fator_conversao && p.fator_conversao > 1 && p.unidade_compra
            ? `<span class="price-pack">${escapeHtml(p.unidade_compra)} · ${p.fator_conversao} un · ${qtdEmbalagens(it.quantidade, p.fator_conversao)} emb. ≈ ${fmtMoney(p.preco_unitario * p.fator_conversao)}/emb.</span>`
            : "";
          if (isFechada) {
            return `<td class="price-cell ${isWinner ? "is-best" : ""}">
              ${p ? fmtMoney(p.preco_unitario) : "—"}
              ${pack}
              ${isWinner ? '<span class="price-best-tag">✓ vencedor</span>' : ""}
            </td>`;
          }
          return `<td class="price-cell ${isBest ? "is-best" : ""}">
            <input class="price-input" type="text" inputmode="decimal"
                   data-item="${it.cotacao_item_id}" data-fornecedor="${f.fornecedor_id}"
                   value="${p != null ? p.preco_unitario : ""}" placeholder="R$">
            ${pack}
            ${isBest ? '<span class="price-best-tag">✓ melhor preço</span>' : ""}
            ${delta ? `<span class="price-delta">+${delta}%</span>` : ""}
          </td>`;
        })
        .join("")}
    </tr>`;
}

function qtdEmbalagens(quantidade: number, fator: number): number {
  if (!fator || fator <= 0) return 1;
  return Math.ceil(quantidade / fator);
}

function renderSummary(
  $app: HTMLElement,
  { itens, vencedores, fornecedores }: { itens: ItemCotacao[]; vencedores: Vencedor[]; fornecedores: CotacaoFornecedor[] }
): void {
  const $wrap = $app.querySelector<HTMLElement>("#summaryWrap")!;
  const fornecedorNome: Record<number, string> = {};
  for (const f of fornecedores) fornecedorNome[f.fornecedor_id] = f.nome;
  let total = 0;
  const porFornecedor: Record<number, number> = {};
  for (const v of vencedores) {
    total += v.preco_unitario * v.quantidade;
    porFornecedor[v.fornecedor_id] = (porFornecedor[v.fornecedor_id] || 0) + v.preco_unitario * v.quantidade;
  }
  $wrap.innerHTML = `
    <div class="summary-box">
      <div class="summary-stat"><span class="label">Total do pedido</span><span class="value">${fmtMoney(total)}</span></div>
      <div class="summary-stat"><span class="label">Itens fechados</span><span class="value">${vencedores.length} / ${itens.length}</span></div>
      ${Object.entries(porFornecedor)
        .map(
          ([fid, val]) => `
            <div class="summary-stat"><span class="label">${escapeHtml(fornecedorNome[Number(fid)] || "—")}</span><span class="value">${fmtMoney(val)}</span></div>
          `
        )
        .join("")}
    </div>`;
}

// ------------------------------------------------------------
// MODAIS
// ------------------------------------------------------------

function abrirModalEditarCotacao($app: HTMLElement, cotacao: CotacaoLista): void {
  openModal(
    `<div class="modal-head"><h3>Editar cotação</h3><button class="icon-btn" data-close>×</button></div>
     <div style="display:flex;flex-direction:column;gap:14px;">
       <div class="field"><label>Título</label><input id="mTitulo" value="${escapeHtml(cotacao.titulo || "")}"></div>
       <div class="field"><label>Cliente</label><input id="mCliente" value="${escapeHtml(cotacao.cliente || "")}"></div>
       <div class="field"><label>Observações</label><textarea id="mObs">${escapeHtml(cotacao.observacoes || "")}</textarea></div>
     </div>
     <div class="modal-actions">
       <button class="btn" data-close>Cancelar</button>
       <button class="btn btn--accent" id="btnSalvar">Salvar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLButtonElement>("#btnSalvar")!.onclick = async () => {
          await api.atualizarCotacao(cotacao.id, {
            titulo: modal.querySelector<HTMLInputElement>("#mTitulo")!.value.trim(),
            cliente: modal.querySelector<HTMLInputElement>("#mCliente")!.value.trim(),
            observacoes: modal.querySelector<HTMLTextAreaElement>("#mObs")!.value.trim(),
          });
          closeModal();
          renderDetalhe($app, cotacao.id);
        };
      },
    }
  );
}

function abrirModalAddFornecedor(
  $app: HTMLElement,
  cotacaoId: number,
  jaConvidados: CotacaoFornecedor[],
  todosFornecedores: Fornecedor[]
): void {
  const jaIds = new Set(jaConvidados.map((f) => f.fornecedor_id));
  const disponiveis = todosFornecedores.filter((f) => !jaIds.has(f.id));

  const corpoDisponiveis = disponiveis.length
    ? `<div style="display:flex;flex-direction:column;gap:2px;max-height:260px;overflow-y:auto;">
         ${disponiveis
           .map(
             (f) => `
               <button class="btn" style="justify-content:flex-start;" data-fid="${f.id}">${escapeHtml(f.nome)}</button>
             `
           )
           .join("")}
       </div>`
    : `
      <p style="font-size:13px;color:var(--ink-soft);margin-bottom:12px;">Nenhum fornecedor ativo disponível para convidar. Cadastre um novo abaixo — ele já será convidado para esta cotação:</p>
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div class="field"><label>Nome *</label><input id="mNome" type="text" placeholder="Nome da empresa / contato"></div>
        <div class="field"><label>WhatsApp</label><input id="mWhats" type="text" placeholder="55DDNÚMERO (só dígitos)"></div>
        <div class="field"><label>E-mail</label><input id="mEmail" type="text"></div>
      </div>`;

  openModal(
    `<div class="modal-head"><h3>Convidar fornecedor</h3><button class="icon-btn" data-close>×</button></div>
     ${corpoDisponiveis}
     <div class="modal-actions">
       <button class="btn" data-close>Cancelar</button>
       ${disponiveis.length
         ? `<button class="btn btn--accent" data-close>Fechar</button>`
         : `<button class="btn btn--accent" id="btnCadastrarConvidar">Cadastrar e convidar</button>`}
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelectorAll<HTMLButtonElement>("[data-fid]").forEach((btn) => {
          btn.onclick = async () => {
            try {
              await api.convidarFornecedor(cotacaoId, Number(btn.dataset.fid));
              closeModal();
              renderDetalhe($app, cotacaoId);
            } catch (e) {
              toast("Erro: " + (e as Error).message, "error");
            }
          };
        });
        const $btnCadastrar = modal.querySelector<HTMLButtonElement>("#btnCadastrarConvidar");
        if ($btnCadastrar) {
          $btnCadastrar.onclick = async () => {
            const nome = modal.querySelector<HTMLInputElement>("#mNome")!.value.trim();
            if (!nome) {
              toast("Informe o nome do fornecedor", "error");
              return;
            }
            try {
              const res = await api.criarFornecedor({
                nome,
                whatsapp: modal.querySelector<HTMLInputElement>("#mWhats")!.value.trim() || null,
                email: modal.querySelector<HTMLInputElement>("#mEmail")!.value.trim() || null,
              });
              await api.convidarFornecedor(cotacaoId, res.id);
              closeModal();
              toast("Fornecedor cadastrado e convidado", "success");
              renderDetalhe($app, cotacaoId);
            } catch (e) {
              toast("Erro: " + (e as Error).message, "error");
            }
          };
        }
      },
    }
  );
}

function abrirModalAddItem($app: HTMLElement, cotacaoId: number): void {
  openModal(
    `<div class="modal-head"><h3>Adicionar item</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field"><label>Buscar produto</label><input id="mBusca" type="text" placeholder="Nome, código, marca…"></div>
     <div id="mResultados" style="max-height:260px;overflow-y:auto;margin-top:10px;"></div>
     <div class="modal-actions"><button class="btn" data-close>Fechar</button></div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        const $busca = modal.querySelector<HTMLInputElement>("#mBusca")!;
        const $res = modal.querySelector<HTMLElement>("#mResultados")!;
        let debounceT: ReturnType<typeof setTimeout> | undefined;
        $busca.addEventListener("input", () => {
          clearTimeout(debounceT);
          debounceT = setTimeout(async () => {
            const q = $busca.value.trim();
            if (q.length < 2) {
              $res.innerHTML = "";
              return;
            }
            const res = await api.listarProdutos({ q, limit: 30, agrupado: 0 });
            const produtos: ProdutoResumo[] = res.items.map((p) => p as ProdutoResumo);
            $res.innerHTML =
              produtos
                .map(
                  (p) => `
                  <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);">
                    ${p.imagem_url ? `<img src="${escapeHtml(p.imagem_url)}" style="width:32px;height:32px;object-fit:contain;background:var(--bg-tray);">` : `<span style="width:32px;"></span>`}
                    <div style="flex:1;font-size:12.5px;">
                      <div style="font-family:var(--font-mono);color:var(--steel);font-size:11px;">${escapeHtml(p.sku || "#" + p.id)}</div>
                      ${escapeHtml(p.name)}
                      ${p.spec ? `<div style="font-size:11px;color:var(--ink-soft);">${escapeHtml(p.spec)}</div>` : ""}
                    </div>
                    <button class="btn btn--sm" data-id="${p.id}">Adicionar</button>
                  </div>`
                )
                .join("") || `<div style="padding:8px 10px;font-size:12.5px;color:var(--ink-faint);">Nada encontrado</div>`;
            $res.querySelectorAll<HTMLButtonElement>("[data-id]").forEach((btn) => {
              btn.onclick = async () => {
                await api.adicionarItem(cotacaoId, { produto_id: Number(btn.dataset.id), quantidade: 1 });
                closeModal();
                renderDetalhe($app, cotacaoId);
              };
            });
          }, 200);
        });
      },
    }
  );
}

function abrirModalFechar(
  $app: HTMLElement,
  {
    cotacaoId,
    itens,
    fornecedores,
    precoMap,
  }: { cotacaoId: number; itens: ItemCotacao[]; fornecedores: CotacaoFornecedor[]; precoMap: Record<string, Preco> }
): void {
  const fornecedorNome: Record<number, string> = {};
  for (const f of fornecedores) fornecedorNome[f.fornecedor_id] = f.nome;
  const rows = itens.map((it) => {
    const options = fornecedores
      .map((f) => precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`])
      .filter(Boolean)
      .sort((a, b) => a.preco_unitario - b.preco_unitario);
    return { item: it, options };
  });
  const semPreco = rows.filter((r) => r.options.length === 0);

  openModal(
    `<div class="modal-head"><h3>Fechar cotação</h3><button class="icon-btn" data-close>×</button></div>
     <p style="font-size:13px;color:var(--ink-soft);margin-bottom:12px;">
       Confirme o fornecedor vencedor de cada item (pré-selecionado o menor preço). Itens sem nenhum preço lançado ficam de fora do pedido fechado.
     </p>
     <div style="display:flex;flex-direction:column;gap:10px;max-height:340px;overflow-y:auto;">
       ${rows
         .filter((r) => r.options.length > 0)
         .map(
           (r) => `
             <div style="border:1px solid var(--line);border-radius:3px;padding:8px 10px;">
               <div style="font-size:12.5px;margin-bottom:6px;"><strong>${escapeHtml(r.item.sku || "#" + r.item.produto_id)}</strong> — ${escapeHtml(r.item.name)} (qtd. ${r.item.quantidade})</div>
               <select class="mSelectVencedor" data-item="${r.item.cotacao_item_id}" style="width:100%;padding:6px;border:1px solid var(--line-strong);border-radius:3px;">
                 ${r.options
                   .map(
                     (p, i) =>
                       `<option value="${p.fornecedor_id}|${p.preco_unitario}" ${i === 0 ? "selected" : ""}>${escapeHtml(fornecedorNome[p.fornecedor_id])} — ${fmtMoney(p.preco_unitario)}</option>`
                   )
                   .join("")}
               </select>
             </div>`
         )
         .join("")}
       ${semPreco.length ? `<p style="font-size:12px;color:var(--ink-faint);">${semPreco.length} item(ns) sem preço lançado não entrarão no pedido.</p>` : ""}
     </div>
     <div class="modal-actions">
       <button class="btn" data-close>Cancelar</button>
       <button class="btn btn--accent" id="btnConfirmarFechar" ${rows.every((r) => r.options.length === 0) ? "disabled" : ""}>Confirmar fechamento</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLButtonElement>("#btnConfirmarFechar")!.onclick = async () => {
          const escolhas = [...modal.querySelectorAll<HTMLSelectElement>(".mSelectVencedor")].map((sel) => {
            const [fornecedor_id, preco_unitario] = sel.value.split("|");
            const item = itens.find((it) => it.cotacao_item_id === Number(sel.dataset.item))!;
            return {
              cotacao_item_id: Number(sel.dataset.item),
              fornecedor_id: Number(fornecedor_id),
              preco_unitario: Number(preco_unitario),
              quantidade: item.quantidade,
            };
          });
          try {
            await api.fecharCotacao(cotacaoId, escolhas);
            closeModal();
            toast("Cotação fechada", "success");
            renderDetalhe($app, cotacaoId);
          } catch (e) {
            toast("Erro ao fechar: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}