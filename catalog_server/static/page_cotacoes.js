// page_cotacoes.js — lista de cotações e tela de comparação/fechamento.
const PageCotacoes = (() => {
  let currentFilter = "";

  // ------------------------------------------------------------
  // LISTA
  // ------------------------------------------------------------
  async function renderLista($app) {
    $app.innerHTML = `<div class="loading">Carregando cotações…</div>`;
    let cotacoes = [];
    try {
      cotacoes = await Api.listarCotacoes(currentFilter || undefined);
    } catch (e) {
      UI.toast("Erro ao carregar cotações: " + e.message, "error");
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

    $app.querySelector("#fStatus").value = currentFilter;
    $app.querySelector("#fStatus").addEventListener("change", (e) => {
      currentFilter = e.target.value;
      renderLista($app);
    });
    $app.querySelectorAll("tr[data-id]").forEach((tr) => {
      tr.addEventListener("click", () => (location.hash = `#/cotacoes/${tr.dataset.id}`));
    });
    $app.querySelectorAll("[data-abrir-comprar]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        sessionStorage.setItem("compras_cotacao", String(btn.dataset.abrirComprar));
        location.hash = "#/compras";
      });
    });
  }

  function emptyList() {
    return `<div class="empty-box"><p>Nenhuma cotação ainda</p><p>Vá até o Catálogo, selecione produtos e crie sua primeira cotação.</p></div>`;
  }

  function listTable(cotacoes) {
    return `
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr>
            <th>Nº</th><th>Título</th><th>Cliente</th><th>Status</th><th>Itens</th><th>Respostas</th><th>Criada em</th><th></th>
          </tr></thead>
          <tbody>
            ${cotacoes.map((c) => `
              <tr data-id="${c.id}" class="row-link">
                <td style="font-family:var(--font-mono);">${c.numero}</td>
                <td>${UI.escapeHtml(c.titulo || "—")}</td>
                <td>${UI.escapeHtml(c.cliente || "—")}</td>
                <td><span class="badge badge--${c.status}">${UI.statusLabel(c.status)}</span></td>
                <td>${c.n_itens}</td>
                <td>${c.n_respostas} / ${c.n_fornecedores}</td>
                <td>${UI.fmtDate(c.criado_em)}</td>
                <td>${c.status === "pendente" || c.status === "analise" || c.status === "finalizada"
                  ? `<button class="btn btn--sm" data-abrir-comprar="${c.id}">Abrir no Comprar</button>` : ""}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  }

  // ------------------------------------------------------------
  // DETALHE / COMPARAÇÃO
  // ------------------------------------------------------------
  async function renderDetalhe($app, cotacaoId) {
    $app.innerHTML = `<div class="loading">Carregando cotação…</div>`;
    let data, todosFornecedores;
    try {
      [data, todosFornecedores] = await Promise.all([
        Api.detalharCotacao(cotacaoId),
        Api.listarFornecedores(true),
      ]);
    } catch (e) {
      $app.innerHTML = `<div class="empty-box"><p>Erro</p><p>${UI.escapeHtml(e.message)}</p></div>`;
      return;
    }
    const { cotacao, itens, fornecedores, precos, vencedores } = data;

    const precoMap = {};
    for (const p of precos) precoMap[`${p.cotacao_item_id}:${p.fornecedor_id}`] = p;
    const vencedorMap = {};
    for (const v of vencedores) vencedorMap[v.cotacao_item_id] = v;

    const isFechada = cotacao.status === "fechada";

    $app.innerHTML = `
      <div class="page-head">
        <div>
          <a href="#/cotacoes" style="font-size:12.5px;color:var(--ink-soft);">← Todas as cotações</a>
          <h1 class="page-title" style="margin-top:6px;">Cotação nº ${cotacao.numero}</h1>
          <p class="page-sub">${UI.escapeHtml(cotacao.titulo || "Sem título")} · criada em ${UI.fmtDateTime(cotacao.criado_em)}${cotacao.cliente ? " · cliente " + UI.escapeHtml(cotacao.cliente) : ""}</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <span class="badge badge--${cotacao.status}">${UI.statusLabel(cotacao.status)}</span>
          <a class="btn btn--sm" href="/orcamentos/${cotacao.id}/imprimir" target="_blank">Imprimir</a>
          <button class="btn btn--ghost btn--sm" id="btnEditar">Editar</button>
          ${isFechada
            ? `<button class="btn btn--sm" id="btnReabrir">Reabrir</button>`
            : `<button class="btn btn--accent btn--sm" id="btnFechar">Fechar cotação</button>`}
        </div>
      </div>

      ${cotacao.observacoes ? `<p style="font-size:13px;color:var(--ink-soft);margin:-8px 0 18px;">Obs.: ${UI.escapeHtml(cotacao.observacoes)}</p>` : ""}

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

    $app.querySelector("#btnEditar").addEventListener("click", () => abrirModalEditarCotacao($app, cotacao));
    if (isFechada) {
      $app.querySelector("#btnReabrir").addEventListener("click", async () => {
        if (!(await UI.confirmDialog("Reabrir esta cotação para novos lançamentos de preço?"))) return;
        await Api.reabrirCotacao(cotacaoId);
        renderDetalhe($app, cotacaoId);
      });
      renderSummary($app, { itens, vencedores, fornecedores });
    } else {
      $app.querySelector("#btnFechar").addEventListener("click", () => abrirModalFechar($app, { cotacaoId, itens, fornecedores, precoMap }));
      $app.querySelector("#btnImportarIA").addEventListener("click", () => {
        PageIA.abrir({
          cotacaoId,
          fornecedores,
          titulo: "Cotação nº " + cotacao.numero,
          onAplicado: () => renderDetalhe($app, cotacaoId),
        });
      });
      $app.querySelector("#btnAddFornecedor").addEventListener("click", () => abrirModalAddFornecedor($app, cotacaoId, fornecedores, todosFornecedores));
      $app.querySelector("#btnAddItem").addEventListener("click", () => abrirModalAddItem($app, cotacaoId));
    }
  }

  function renderCompareTable($app, { cotacaoId, itens, fornecedores, precoMap, vencedorMap, isFechada }) {
    const $wrap = $app.querySelector("#compareWrap");
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
              ${fornecedores.map((f) => `<th>${UI.escapeHtml(f.nome)}<br><span class="badge badge--${f.status}" style="margin-top:4px;">${UI.statusLabel(f.status)}</span></th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${itens.map((it) => rowHtml(it, fornecedores, precoMap, vencedorMap, isFechada)).join("")}
          </tbody>
        </table>
      </div>`;

    if (!isFechada) {
      $wrap.querySelectorAll(".price-input").forEach((input) => {
        input.addEventListener("change", async (e) => {
          const val = parseFloat(e.target.value.replace(",", "."));
          const itemId = Number(e.target.dataset.item);
          const fornecedorId = Number(e.target.dataset.fornecedor);
          if (isNaN(val) || val < 0) {
            UI.toast("Preço inválido", "error");
            return;
          }
          try {
            await Api.registrarPreco(cotacaoId, { cotacao_item_id: itemId, fornecedor_id: fornecedorId, preco_unitario: val });
            UI.toast("Preço registrado", "success");
            renderDetalhe($app, cotacaoId);
          } catch (err) {
            UI.toast("Erro: " + err.message, "error");
          }
        });
      });
      $wrap.querySelectorAll(".btn-remove-item").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!(await UI.confirmDialog("Remover este item da cotação?"))) return;
          await Api.removerItem(cotacaoId, Number(btn.dataset.item));
          renderDetalhe($app, cotacaoId);
        });
      });
    }
  }

  function rowHtml(it, fornecedores, precoMap, vencedorMap, isFechada) {
    const rowPrecos = fornecedores.map((f) => precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`]).filter(Boolean);
    const best = rowPrecos.length ? Math.min(...rowPrecos.map((p) => p.preco_unitario)) : null;
    const vencedor = vencedorMap[it.cotacao_item_id];

    return `
      <tr>
        <td>
          <div class="compare-item-cell">
            ${it.imagem_url ? `<img src="${UI.escapeHtml(it.imagem_url)}" alt="">` : `<span style="width:34px;"></span>`}
            <div>
              <div class="compare-item-code">${UI.escapeHtml(it.sku || "#" + it.produto_id)}</div>
              <div class="compare-item-desc">${UI.escapeHtml(it.name)}</div>
            </div>
            ${isFechada ? "" : `<button class="icon-btn btn-remove-item" data-item="${it.cotacao_item_id}" style="margin-left:auto;" title="Remover item">×</button>`}
          </div>
        </td>
        <td class="qty-col">${it.quantidade}</td>
        ${fornecedores.map((f) => {
          const p = precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`];
          const isBest = p && best !== null && p.preco_unitario === best;
          const isWinner = vencedor && vencedor.fornecedor_id === f.fornecedor_id;
          const delta = p && best !== null && !isBest ? (((p.preco_unitario - best) / best) * 100).toFixed(1) : null;
          if (isFechada) {
            return `<td class="price-cell ${isWinner ? "is-best" : ""}">
              ${p ? UI.fmtMoney(p.preco_unitario) : "—"}
              ${isWinner ? '<span class="price-best-tag">✓ vencedor</span>' : ""}
            </td>`;
          }
          return `<td class="price-cell ${isBest ? "is-best" : ""}">
            <input class="price-input" type="text" inputmode="decimal"
                   data-item="${it.cotacao_item_id}" data-fornecedor="${f.fornecedor_id}"
                   value="${p ? p.preco_unitario : ""}" placeholder="R$">
            ${isBest ? '<span class="price-best-tag">✓ melhor preço</span>' : ""}
            ${delta ? `<span class="price-delta">+${delta}%</span>` : ""}
          </td>`;
        }).join("")}
      </tr>`;
  }

  function renderSummary($app, { itens, vencedores, fornecedores }) {
    const $wrap = $app.querySelector("#summaryWrap");
    const fornecedorNome = Object.fromEntries(fornecedores.map((f) => [f.fornecedor_id, f.nome]));
    let total = 0;
    const porFornecedor = {};
    for (const v of vencedores) {
      total += v.preco_unitario * v.quantidade;
      porFornecedor[v.fornecedor_id] = (porFornecedor[v.fornecedor_id] || 0) + v.preco_unitario * v.quantidade;
    }
    $wrap.innerHTML = `
      <div class="summary-box">
        <div class="summary-stat"><span class="label">Total do pedido</span><span class="value">${UI.fmtMoney(total)}</span></div>
        <div class="summary-stat"><span class="label">Itens fechados</span><span class="value">${vencedores.length} / ${itens.length}</span></div>
        ${Object.entries(porFornecedor).map(([fid, val]) => `
          <div class="summary-stat"><span class="label">${UI.escapeHtml(fornecedorNome[fid] || "—")}</span><span class="value">${UI.fmtMoney(val)}</span></div>
        `).join("")}
      </div>`;
  }

  // ------------------------------------------------------------
  // MODAIS
  // ------------------------------------------------------------
  function abrirModalEditarCotacao($app, cotacao) {
    UI.openModal(
      `<div class="modal-head"><h3>Editar cotação</h3><button class="icon-btn" data-close>×</button></div>
       <div style="display:flex;flex-direction:column;gap:14px;">
         <div class="field"><label>Título</label><input id="mTitulo" value="${UI.escapeHtml(cotacao.titulo || "")}"></div>
         <div class="field"><label>Cliente</label><input id="mCliente" value="${UI.escapeHtml(cotacao.cliente || "")}"></div>
         <div class="field"><label>Observações</label><textarea id="mObs">${UI.escapeHtml(cotacao.observacoes || "")}</textarea></div>
       </div>
       <div class="modal-actions">
         <button class="btn" data-close>Cancelar</button>
         <button class="btn btn--accent" id="btnSalvar">Salvar</button>
       </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          modal.querySelector("#btnSalvar").onclick = async () => {
            await Api.atualizarCotacao(cotacao.id, {
              titulo: modal.querySelector("#mTitulo").value.trim(),
              cliente: modal.querySelector("#mCliente").value.trim(),
              observacoes: modal.querySelector("#mObs").value.trim(),
            });
            UI.closeModal();
            renderDetalhe($app, cotacao.id);
          };
        },
      }
    );
  }

  function abrirModalAddFornecedor($app, cotacaoId, jaConvidados, todosFornecedores) {
    const jaIds = new Set(jaConvidados.map((f) => f.fornecedor_id));
    const disponiveis = todosFornecedores.filter((f) => !jaIds.has(f.id));

    const corpoDisponiveis = disponiveis.length
      ? `<div style="display:flex;flex-direction:column;gap:2px;max-height:260px;overflow-y:auto;">
           ${disponiveis.map((f) => `
             <button class="btn" style="justify-content:flex-start;" data-fid="${f.id}">${UI.escapeHtml(f.nome)}</button>
           `).join("")}
         </div>`
      : `
        <p style="font-size:13px;color:var(--ink-soft);margin-bottom:12px;">Nenhum fornecedor ativo disponível para convidar. Cadastre um novo abaixo — ele já será convidado para esta cotação:</p>
        <div style="display:flex;flex-direction:column;gap:12px;">
          <div class="field"><label>Nome *</label><input id="mNome" type="text" placeholder="Nome da empresa / contato"></div>
          <div class="field"><label>WhatsApp</label><input id="mWhats" type="text" placeholder="55DDNÚMERO (só dígitos)"></div>
          <div class="field"><label>E-mail</label><input id="mEmail" type="text"></div>
        </div>`;

    UI.openModal(
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
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          modal.querySelectorAll("[data-fid]").forEach((btn) => {
            btn.onclick = async () => {
              try {
                await Api.convidarFornecedor(cotacaoId, Number(btn.dataset.fid));
                UI.closeModal();
                renderDetalhe($app, cotacaoId);
              } catch (e) {
                UI.toast("Erro: " + e.message, "error");
              }
            };
          });
          const $btnCadastrar = modal.querySelector("#btnCadastrarConvidar");
          if ($btnCadastrar) {
            $btnCadastrar.onclick = async () => {
              const nome = modal.querySelector("#mNome").value.trim();
              if (!nome) {
                UI.toast("Informe o nome do fornecedor", "error");
                return;
              }
              try {
                const res = await Api.criarFornecedor({
                  nome,
                  whatsapp: modal.querySelector("#mWhats").value.trim() || null,
                  email: modal.querySelector("#mEmail").value.trim() || null,
                });
                await Api.convidarFornecedor(cotacaoId, res.id);
                UI.closeModal();
                UI.toast("Fornecedor cadastrado e convidado", "success");
                renderDetalhe($app, cotacaoId);
              } catch (e) {
                UI.toast("Erro: " + e.message, "error");
              }
            };
          }
        },
      }
    );
  }

  function abrirModalAddItem($app, cotacaoId) {
    UI.openModal(
      `<div class="modal-head"><h3>Adicionar item</h3><button class="icon-btn" data-close>×</button></div>
       <div class="field"><label>Buscar produto</label><input id="mBusca" type="text" placeholder="Nome, código, marca…"></div>
       <div id="mResultados" style="max-height:260px;overflow-y:auto;margin-top:10px;"></div>
       <div class="modal-actions"><button class="btn" data-close>Fechar</button></div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          const $busca = modal.querySelector("#mBusca");
          const $res = modal.querySelector("#mResultados");
          let debounceT;
          $busca.addEventListener("input", () => {
            clearTimeout(debounceT);
            debounceT = setTimeout(async () => {
              const q = $busca.value.trim();
              if (q.length < 2) {
                $res.innerHTML = "";
                return;
              }
              const res = await Api.listarProdutos({ q, limit: 30, agrupado: 0 });
              const produtos = res.items || [];
              $res.innerHTML = produtos.map((p) => `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);">
                  ${p.imagem_url ? `<img src="${UI.escapeHtml(p.imagem_url)}" style="width:32px;height:32px;object-fit:contain;background:var(--bg-tray);">` : `<span style="width:32px;"></span>`}
                  <div style="flex:1;font-size:12.5px;">
                    <div style="font-family:var(--font-mono);color:var(--steel);font-size:11px;">${UI.escapeHtml(p.sku || "#" + p.id)}</div>
                    ${UI.escapeHtml(p.name)}
                    ${p.spec ? `<div style="font-size:11px;color:var(--ink-soft);">${UI.escapeHtml(p.spec)}</div>` : ""}
                  </div>
                  <button class="btn btn--sm" data-id="${p.id}">Adicionar</button>
                </div>`).join("") || `<div style="padding:8px 10px;font-size:12.5px;color:var(--ink-faint);">Nada encontrado</div>`;
              $res.querySelectorAll("[data-id]").forEach((btn) => {
                btn.onclick = async () => {
                  await Api.adicionarItem(cotacaoId, { produto_id: Number(btn.dataset.id), quantidade: 1 });
                  UI.closeModal();
                  renderDetalhe($app, cotacaoId);
                };
              });
            }, 200);
          });
        },
      }
    );
  }

  function abrirModalFechar($app, { cotacaoId, itens, fornecedores, precoMap }) {
    const fornecedorNome = Object.fromEntries(fornecedores.map((f) => [f.fornecedor_id, f.nome]));
    const rows = itens.map((it) => {
      const options = fornecedores
        .map((f) => precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`])
        .filter(Boolean)
        .sort((a, b) => a.preco_unitario - b.preco_unitario);
      return { item: it, options };
    });
    const semPreco = rows.filter((r) => r.options.length === 0);

    UI.openModal(
      `<div class="modal-head"><h3>Fechar cotação</h3><button class="icon-btn" data-close>×</button></div>
       <p style="font-size:13px;color:var(--ink-soft);margin-bottom:12px;">
         Confirme o fornecedor vencedor de cada item (pré-selecionado o menor preço). Itens sem nenhum preço lançado ficam de fora do pedido fechado.
       </p>
       <div style="display:flex;flex-direction:column;gap:10px;max-height:340px;overflow-y:auto;">
         ${rows.filter((r) => r.options.length > 0).map((r) => `
           <div style="border:1px solid var(--line);border-radius:3px;padding:8px 10px;">
             <div style="font-size:12.5px;margin-bottom:6px;"><strong>${UI.escapeHtml(r.item.sku || "#" + r.item.produto_id)}</strong> — ${UI.escapeHtml(r.item.name)} (qtd. ${r.item.quantidade})</div>
             <select class="mSelectVencedor" data-item="${r.item.cotacao_item_id}" style="width:100%;padding:6px;border:1px solid var(--line-strong);border-radius:3px;">
               ${r.options.map((p, i) => `<option value="${p.fornecedor_id}|${p.preco_unitario}" ${i === 0 ? "selected" : ""}>${UI.escapeHtml(fornecedorNome[p.fornecedor_id])} — ${UI.fmtMoney(p.preco_unitario)}</option>`).join("")}
             </select>
           </div>`).join("")}
         ${semPreco.length ? `<p style="font-size:12px;color:var(--ink-faint);">${semPreco.length} item(ns) sem preço lançado não entrarão no pedido.</p>` : ""}
       </div>
       <div class="modal-actions">
         <button class="btn" data-close>Cancelar</button>
         <button class="btn btn--accent" id="btnConfirmarFechar" ${rows.every((r) => r.options.length === 0) ? "disabled" : ""}>Confirmar fechamento</button>
       </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          modal.querySelector("#btnConfirmarFechar").onclick = async () => {
            const escolhas = [...modal.querySelectorAll(".mSelectVencedor")].map((sel) => {
              const [fornecedor_id, preco_unitario] = sel.value.split("|");
              const item = itens.find((it) => it.cotacao_item_id === Number(sel.dataset.item));
              return {
                cotacao_item_id: Number(sel.dataset.item),
                fornecedor_id: Number(fornecedor_id),
                preco_unitario: Number(preco_unitario),
                quantidade: item.quantidade,
              };
            });
            try {
              await Api.fecharCotacao(cotacaoId, escolhas);
              UI.closeModal();
              UI.toast("Cotação fechada", "success");
              renderDetalhe($app, cotacaoId);
            } catch (e) {
              UI.toast("Erro ao fechar: " + e.message, "error");
            }
          };
        },
      }
    );
  }

  return { renderLista, renderDetalhe };
})();
