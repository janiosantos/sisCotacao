// page_produtos.js — cadastro de produtos (famílias + produto pai + variações + imagens).
const PageProdutos = (() => {
  let familias = [];
  let categoriasSugestoes = [];
  let categoriasTree = {};
  let fornecedores = [];           // lista p/ códigos por fornecedor

  // ---------------- estado da lista ----------------
  let filters = { q: "", familia_id: "" };
  let items = [];
  let total = 0;
  let page = 1;
  let loading = false;
  const PAGE = 60;

  // ---------------- estado do editor ----------------
  let atributos = [];            // defs da família selecionada
  let valores = {};              // attrId -> Set(valores)
  let variantes = [];            // {id?, sku, ean, preco, prom, valores:{attrId:value}}
  let editingProduto = null;     // produto em edição (ou null)
  let fornecedorEdits = {};      // "fornecedorId:varianteId" -> {codigo, unidade, fator, descricao}

  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  async function carregarCategorias() {
    try {
      const tree = await Api.listarCategorias();
      categoriasTree = tree;
      const list = [];
      for (const [cat, subs] of Object.entries(tree)) {
        list.push(cat);
        (subs || []).forEach((s) => list.push(`${cat} > ${s}`));
      }
      categoriasSugestoes = [...new Set(list)].sort((a, b) => a.localeCompare(b, "pt"));
    } catch (e) { categoriasSugestoes = []; categoriasTree = {}; }
  }

  function atualizarSubsugestoes(categoria) {
    const subs = (categoriasTree[categoria] || [])
      .slice()
      .sort((a, b) => a.localeCompare(b, "pt"));
    const dl = document.getElementById("dlSubcategorias");
    if (dl) dl.innerHTML = subs.map((s) => `<option value="${UI.escapeHtml(s)}">`).join("");
  }

  // ===================================================================
  // LISTA
  // ===================================================================

  async function renderLista($app) {
    $app.innerHTML = `<div class="loading">Carregando produtos…</div>`;
    try {
      familias = await Api.listarFamilias();
    } catch (e) { familias = []; }
    await carregarCategorias();

    $app.innerHTML = `
      <div class="page-head">
        <div>
          <h1 class="page-title">Produtos</h1>
          <p class="page-sub">Cadastre produtos por família e geração de variações (modelo TOTVS).</p>
        </div>
      </div>

      <div class="toolbar">
        <div class="field" style="min-width:240px;flex:1;">
          <label>Buscar</label>
          <input id="fSearch" type="text" placeholder="Nome, marca, código…" autocomplete="off">
          <p class="search-hint" id="searchHint">Digite ao menos 3 caracteres para buscar.</p>
        </div>
        <div class="field">
          <label>Família</label>
          <select id="fFamilia"><option value="">Todas</option></select>
        </div>
        <button class="btn btn--outline" id="btnFamilias">Famílias</button>
        <button class="btn btn--outline" id="btnNovoUrl">Novo via URL</button>
        <button class="btn btn--accent" id="btnNovo">Novo produto</button>
        <span class="result-count" id="resultCount"></span>
      </div>

      <div id="grid" class="product-grid"></div>
      <div class="load-more" id="paginacao"></div>
    `;

    const $familia = $app.querySelector("#fFamilia");
    for (const f of familias) {
      $familia.insertAdjacentHTML("beforeend", `<option value="${f.id}">${UI.escapeHtml(f.nome)}</option>`);
    }

    const $search = $app.querySelector("#fSearch");
    const $hint = $app.querySelector("#searchHint");
    $search.addEventListener("input", debounce((e) => {
      const v = e.target.value.trim();
      if (v.length > 0 && v.length < 3) {
        $hint.style.display = "block";
        if (filters.q !== "") { filters.q = ""; carregar($app, true); }
        return;
      }
      $hint.style.display = "none";
      filters.q = v;
      carregar($app, true);
    }, 300));
    $familia.addEventListener("change", (e) => {
      filters.familia_id = e.target.value;
      carregar($app, true);
    });
    $app.querySelector("#btnFamilias").addEventListener("click", () => abrirModalFamilias($app));
    $app.querySelector("#btnNovoUrl").addEventListener("click", () => abrirModalImportarUrl($app));
    $app.querySelector("#btnNovo").addEventListener("click", () => { location.hash = "#/produtos/novo"; });

    carregar($app, true);
  }

  async function carregar($app, reset) {
    if (loading) return;
    if (reset) page = 1;
    loading = true;
    const $grid = $app.querySelector("#grid");
    try {
      const res = await Api.listarProdutosCadastro({
        q: filters.q,
        familia_id: filters.familia_id || undefined,
        offset: (page - 1) * PAGE,
        limit: PAGE,
      });
      items = res.items;
      total = res.total;
      renderGrid($app);
      renderPaginacao($app);
    } catch (e) {
      UI.toast("Erro ao carregar produtos: " + e.message, "error");
    } finally {
      loading = false;
    }
  }

  function renderPaginacao($app) {
    const $wrap = $app.querySelector("#paginacao");
    const paginas = Math.max(1, Math.ceil(total / PAGE));
    if (paginas <= 1) { $wrap.innerHTML = ""; return; }
    const atual = Math.min(Math.max(1, page), paginas);
    const botoes = [];
    const addBtn = (label, p, opts = {}) => {
      botoes.push(`<button class="btn btn--sm pg-btn ${opts.active ? "btn--accent" : ""}" data-page="${p}" ${opts.disabled ? "disabled" : ""}>${label}</button>`);
    };
    addBtn("«", atual - 1, { disabled: atual <= 1 });
    const inicio = Math.max(1, atual - 3);
    const fim = Math.min(paginas, atual + 3);
    if (inicio > 1) {
      addBtn("1", 1);
      if (inicio > 2) botoes.push('<span class="pg-ellipsis">…</span>');
    }
    for (let p = inicio; p <= fim; p++) addBtn(String(p), p, { active: p === atual });
    if (fim < paginas) {
      if (fim < paginas - 1) botoes.push('<span class="pg-ellipsis">…</span>');
      addBtn(String(paginas), paginas);
    }
    addBtn("»", atual + 1, { disabled: atual >= paginas });
    $wrap.innerHTML = `
      <div class="pagination">
        <span class="pg-info">Página ${atual} de ${paginas} · ${total} produto(s)</span>
        <div class="pg-btns">${botoes.join("")}</div>
      </div>`;
    $wrap.querySelectorAll("[data-page]").forEach((b) => {
      if (b.disabled) return;
      b.onclick = () => { page = Number(b.dataset.page); carregar($app, false); };
    });
  }

  function renderGrid($app) {
    $app.querySelector("#resultCount").textContent = `${total} produto(s)`;
    const $grid = $app.querySelector("#grid");
    if (!items.length) {
      $grid.innerHTML = filters.q
        ? `<div class="empty-box" style="grid-column:1/-1;"><p>Nenhum produto encontrado para a busca.</p><p>Confira os termos digitados ou busque por SKU/EAN.</p></div>`
        : `<div class="empty-box" style="grid-column:1/-1;"><p>Nenhum produto cadastrado</p><p>Clique em "Novo produto" para começar.</p></div>`;
      return;
    }
    $grid.innerHTML = items.map(cardHtml).join("");
    $grid.querySelectorAll(".p-card").forEach((card) => {
      const id = Number(card.dataset.id);
      card.querySelector(".p-pick").addEventListener("click", () => { location.hash = `#/produtos/${id}`; });
      card.querySelector(".p-del").addEventListener("click", async (e) => {
        e.stopPropagation();
        const ok = await UI.confirmDialog("Excluir este produto e todas as suas variações e imagens?");
        if (!ok) return;
        try {
          await Api.excluirProdutoCadastro(id);
          UI.toast("Produto excluído", "success");
          carregar($app, true);
        } catch (err) {
          UI.toast("Erro ao excluir: " + err.message, "error");
        }
      });
    });
  }

  function cardHtml(p) {
    const price = p.price_min ? `a partir de ${UI.fmtMoney(p.price_min)}` : "sem preço";
    const badgeClasse = p.classe_abc
      ? `<span class="abc-chip abc-chip--${p.classe_abc.toLowerCase()}">${p.classe_abc}</span>`
      : "";
    const badgeLinha = p.em_linha === 0
      ? `<span class="abc-chip abc-chip--fora" title="Fora do rolar (equipamento de alto valor)">fora</span>`
      : "";
    return `
      <article class="p-card" data-id="${p.id}">
        <div class="p-photo">${p.imagem_url ? `<img src="${UI.escapeHtml(p.imagem_url)}" loading="lazy" alt="">` : `<span style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">sem imagem</span>`}</div>
        <div class="p-body">
          <p class="p-code"><span class="p-badge">${UI.escapeHtml(p.familia_nome || "Sem família")}</span> ${p.variant_count} variações ${badgeClasse} ${badgeLinha}</p>
          <p class="p-desc">${UI.escapeHtml(p.nome)}</p>
          ${p.marca ? `<p class="p-brand">${UI.escapeHtml(p.marca)}</p>` : ""}
          <p class="p-price">${price}</p>
        </div>
        <div class="p-actions" style="display:flex;gap:6px;align-items:center;">
          <button class="btn btn--accent btn--sm p-pick">Editar</button>
          <button class="btn btn--danger btn--sm p-del">Excluir</button>
        </div>
      </article>`;
  }

  // ===================================================================
  // FAMÍLIAS (gestão)
  // ===================================================================

  async function abrirModalFamilias($app) {
    const refresh = async () => {
      familias = await Api.listarFamilias();
      renderLista($app);
    };
    const corpo = () => {
      if (!familias.length) return `<p style="font-size:13px;color:var(--ink-soft);">Nenhuma família cadastrada ainda.</p>`;
      return familias.map((f) => `
        <div class="fam-row">
          <div style="flex:1;">
            <strong>${UI.escapeHtml(f.nome)}</strong>
            <div style="font-size:12px;color:var(--ink-soft);">${f.atributos.length} atributo(s): ${UI.escapeHtml(f.atributos.map((a) => a.nome).join(", "))}</div>
          </div>
          <button class="btn btn--sm" data-edit="${f.id}">Editar</button>
          <button class="btn btn--danger btn--sm" data-del="${f.id}">Excluir</button>
        </div>`).join("");
    };
    UI.openModal(`
      <div class="modal-head"><h3>Famílias</h3><button class="icon-btn" data-close>×</button></div>
      <div id="famLista" style="display:flex;flex-direction:column;gap:8px;max-height:60vh;overflow-y:auto;">${corpo()}</div>
      <div class="modal-actions">
        <button class="btn" data-close>Fechar</button>
        <button class="btn btn--accent" id="btnNovaFamilia">Nova família</button>
      </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          modal.querySelectorAll("[data-edit]").forEach((b) => {
            b.onclick = async () => {
              const f = familias.find((x) => x.id === Number(b.dataset.edit));
              const saved = await abrirModalFamiliaForm(f);
              if (saved) { UI.closeModal(); refresh(); }
            };
          });
          modal.querySelectorAll("[data-del]").forEach((b) => {
            b.onclick = async () => {
              const f = familias.find((x) => x.id === Number(b.dataset.del));
              if (!(await UI.confirmDialog(`Excluir a família "${f.nome}"?`))) return;
              try {
                await Api.excluirFamilia(f.id);
                UI.toast("Família excluída", "success");
                refresh();
              } catch (e) {
                UI.toast("Erro: " + e.message, "error");
              }
            };
          });
          modal.querySelector("#btnNovaFamilia").onclick = async () => {
            const saved = await abrirModalFamiliaForm(null);
            if (saved) { UI.closeModal(); refresh(); }
          };
        },
      }
    );
  }

  function abrirModalFamiliaForm(familia) {
    return new Promise((resolve) => {
      let atributos = (familia ? familia.atributos : []).map((a) => ({
        id: a.id, nome: a.nome, tipo: a.tipo, opcoes: a.opcoes || [], obrigatorio: !!a.obrigatorio,
      }));
      if (!atributos.length) atributos = [{ id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false }];

      const rowHtml = (a, i) => `
        <div class="fa-row" data-i="${i}">
          <input class="fa-nome" data-i="${i}" type="text" placeholder="Nome do atributo (ex.: Cor)" value="${UI.escapeHtml(a.nome)}">
          <select class="fa-tipo" data-i="${i}">
            <option value="lista" ${a.tipo === "lista" ? "selected" : ""}>Lista de opções</option>
            <option value="livre" ${a.tipo === "livre" ? "selected" : ""}>Valor livre</option>
          </select>
          <input class="fa-opcoes" data-i="${i}" type="text" placeholder="azul, vermelho, preto (separado por vírgula)" value="${UI.escapeHtml(a.opcoes.join(", "))}">
          <label class="fa-obrig" title="Obriga a informar ao menos um valor deste atributo ao cadastrar o produto">
            <input type="checkbox" class="fa-obrig-check" data-i="${i}" ${a.obrigatorio ? "checked" : ""}> Obrig.
          </label>
          <button class="icon-btn" data-rm="${i}">×</button>
        </div>`;

      const corpo = () => `
        <div class="modal-head"><h3>${familia ? "Editar família" : "Nova família"}</h3><button class="icon-btn" data-close>×</button></div>
        <div style="display:flex;flex-direction:column;gap:12px;">
          <div class="field"><label>Nome da família *</label><input id="faNome" type="text" value="${UI.escapeHtml(familia ? familia.nome : "")}" placeholder="Ex.: Cabo Flexível, Parafuso, Cola"></div>
          <div class="field"><label>Descrição (opcional)</label><input id="faDesc" type="text" value="${UI.escapeHtml(familia ? familia.descricao : "")}"></div>
          <div class="field">
            <label>Atributos (características das variações)</label>
            <div id="faLista" style="display:flex;flex-direction:column;gap:6px;">${atributos.map(rowHtml).join("")}</div>
            <button class="btn btn--ghost btn--sm" id="faAdd" style="margin-top:8px;">+ Adicionar atributo</button>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn" data-cancel>Cancelar</button>
          <button class="btn btn--accent" id="faSalvar">Salvar</button>
        </div>`;

      UI.openModal(corpo(), {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          modal.querySelector("[data-cancel]").onclick = () => { UI.closeModal(); resolve(false); };

          function collect() {
            return atributos.map((a, i) => ({
              id: a.id,
              nome: modal.querySelector(`.fa-nome[data-i="${i}"]`).value.trim(),
              tipo: modal.querySelector(`.fa-tipo[data-i="${i}"]`).value,
              opcoes: modal.querySelector(`.fa-opcoes[data-i="${i}"]`).value
                .split(",").map((s) => s.trim()).filter(Boolean),
              obrigatorio: !!modal.querySelector(`.fa-obrig-check[data-i="${i}"]`).checked,
            })).filter((a) => a.nome);
          }
          function syncFromDom() {
            modal.querySelectorAll("#faLista .fa-row").forEach((row, i) => {
              if (!atributos[i]) return;
              atributos[i].nome = row.querySelector(".fa-nome").value;
              atributos[i].tipo = row.querySelector(".fa-tipo").value;
              atributos[i].opcoes = row.querySelector(".fa-opcoes").value
                .split(",").map((s) => s.trim()).filter(Boolean);
              atributos[i].obrigatorio = !!row.querySelector(".fa-obrig-check").checked;
            });
          }
          function rebuild() {
            syncFromDom();
            modal.querySelector("#faLista").innerHTML = atributos.map(rowHtml).join("");
            modal.querySelector("#faLista").querySelectorAll("[data-rm]").forEach((b) => {
              b.onclick = () => { atributos.splice(Number(b.dataset.rm), 1); rebuild(); };
            });
          }
          modal.querySelectorAll("#faLista [data-rm]").forEach((b) => {
            b.onclick = () => { atributos.splice(Number(b.dataset.rm), 1); rebuild(); };
          });
          modal.querySelector("#faAdd").onclick = () => {
            atributos.push({ id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false });
            rebuild();
          };
          modal.querySelector("#faSalvar").onclick = async () => {
            const nome = modal.querySelector("#faNome").value.trim();
            if (!nome) { UI.toast("Informe o nome da família", "error"); return; }
            const payload = { nome, descricao: modal.querySelector("#faDesc").value.trim(), atributos: collect() };
            try {
              if (familia) {
                await Api.atualizarFamilia(familia.id, payload);
                resolve(true);
              } else {
                const res = await Api.criarFamilia(payload);
                resolve({ id: res.id, nome });
              }
              UI.toast("Família salva", "success");
            } catch (e) {
              UI.toast("Erro: " + e.message, "error");
            }
          };
        },
      });
    });
  }

  // ===================================================================
  // IMPORTAR POR URL
  // ===================================================================

  function previewHtml(p) {
    const linhas = [
      ["Produto", p.nome],
      ["Marca", p.marca],
      ["SKU / EAN", [p.sku, p.ean].filter(Boolean).join(" / ")],
      ["Família", p.familia_nome],
      ["Preço", p.preco != null ? UI.fmtMoney(p.preco) : "—"],
      ["À vista (PIX)", p.preco_pix != null ? UI.fmtMoney(p.preco_pix) : "—"],
      ["De", p.preco_de != null ? UI.fmtMoney(p.preco_de) : "—"],
      ["Parcelamento", p.parcelamento],
      ["Fotos", p.fotos],
    ];
    const attrs = (p.atributos || []).map((a) => `${UI.escapeHtml(a.label)}: <strong>${UI.escapeHtml(a.valor)}</strong>`).join(" · ");
    return `
      <div class="preview-box" style="border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:12px;">
        <table style="width:100%;font-size:13px;border-collapse:collapse;">
          ${linhas.filter(([, v]) => v).map(([k, v]) => `
            <tr style="border-bottom:1px solid var(--line);">
              <td style="padding:5px 8px;color:var(--ink-soft);width:140px;">${k}</td>
              <td style="padding:5px 8px;"><strong>${UI.escapeHtml(String(v))}</strong></td>
            </tr>`).join("")}
          ${attrs ? `<tr><td style="padding:5px 8px;color:var(--ink-soft);vertical-align:top;">Atributos</td><td style="padding:5px 8px;">${attrs}</td></tr>` : ""}
        </table>
      </div>`;
  }

  function abrirModalImportarUrl($app) {
    UI.openModal(`
      <div class="modal-head"><h3>Cadastrar a partir de URL</h3><button class="icon-btn" data-close>×</button></div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <div class="field">
          <label>URL do produto</label>
          <input id="iuUrl" type="text" placeholder="https://www.casadoeletricistasc.com.br/...">
        </div>
        <p style="font-size:12px;color:var(--ink-soft);">O sistema lê a página e cria automaticamente a família, os atributos e baixa as fotos. Você confere o resultado antes de confirmar.</p>
        <div id="iuPreview"></div>
      </div>
      <div class="modal-actions">
        <button class="btn" data-close>Cancelar</button>
        <button class="btn btn--accent" id="iuAnalisar">Analisar URL</button>
        <button class="btn btn--accent" id="iuCadastrar" style="display:none;">Cadastrar produto</button>
      </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          const $url = modal.querySelector("#iuUrl");
          const $prev = modal.querySelector("#iuPreview");
          const $analisar = modal.querySelector("#iuAnalisar");
          const $cadastrar = modal.querySelector("#iuCadastrar");
          let parsed = null;

          $analisar.onclick = async () => {
            const url = $url.value.trim();
            if (!url) { UI.toast("Informe a URL do produto", "error"); return; }
            $analisar.disabled = true;
            $analisar.textContent = "Analisando…";
            $prev.innerHTML = `<p style="font-size:13px;color:var(--ink-soft);">Buscando informações do produto…</p>`;
            try {
              parsed = await Api.parseUrlProduto(url);
              $prev.innerHTML = previewHtml(parsed);
              $cadastrar.style.display = "";
              UI.toast("Produto identificado", "success");
            } catch (e) {
              $prev.innerHTML = `<p style="font-size:13px;color:var(--ink-faint);">Erro: ${UI.escapeHtml(e.message)}</p>`;
            } finally {
              $analisar.disabled = false;
              $analisar.textContent = "Analisar URL";
            }
          };

          $cadastrar.onclick = async () => {
            if (!parsed) return;
            $cadastrar.disabled = true;
            $cadastrar.textContent = "Cadastrando…";
            try {
              const res = await Api.criarProdutoPorUrl(parsed.url);
              UI.closeModal();
              UI.toast(`Produto cadastrado (${res.imagens_baixadas} foto(s) baixada(s))`, "success");
              if (res.imagens_erros) UI.toast(`${res.imagens_erros} foto(s) não puderam ser baixadas`, "error");
              location.hash = `#/produtos/${res.id}`;
            } catch (e) {
              UI.toast("Erro ao cadastrar: " + e.message, "error");
              $cadastrar.disabled = false;
              $cadastrar.textContent = "Cadastrar produto";
            }
          };
        },
      }
    );
  }

  // ===================================================================
  // EDITOR DE PRODUTO
  // ===================================================================

  async function renderEditor($app, produtoId) {
    $app.innerHTML = `<div class="loading">Carregando…</div>`;
    if (!familias.length) {
      try { familias = await Api.listarFamilias(); } catch (e) { familias = []; }
    }
    await carregarCategorias();

    let produto = null;
    if (produtoId) {
      try { produto = await Api.detalharProdutoCadastro(produtoId); }
      catch (e) { UI.toast("Erro ao carregar produto", "error"); location.hash = "#/produtos"; return; }
    }

    editingProduto = produto;
    const familiaInicial = produto ? produto.familia_id : (familias[0] ? familias[0].id : null);
    carregarAtributosFamilia(familiaInicial, produto);

    $app.innerHTML = `
      <div class="page-head">
        <div>
          <h1 class="page-title">${produto ? "Editar produto" : "Novo produto"}</h1>
          <p class="page-sub">Cadastre o produto uma vez; as variações são geradas pelas combinações dos atributos.</p>
        </div>
        <button class="btn btn--ghost" id="btnVoltar">← Voltar</button>
      </div>

      <div class="erp-editor">

        <!-- Abas corporativas (Folders) -->
        <div class="erp-tabs" role="tablist">
          <button type="button" class="erp-tab is-active" data-tab="gerais">Dados Gerais</button>
          <button type="button" class="erp-tab" data-tab="atributos">Atributos da Família</button>
          <button type="button" class="erp-tab" data-tab="variacoes">Matriz de Variações</button>
          <button type="button" class="erp-tab" data-tab="imagens">Mídia e Anexos</button>
        </div>

        <!-- Aba 1: Dados Gerais (com painel de gestão / Curva ABC) -->
        <div class="erp-panel is-active" id="tab-gerais">
          <div class="ed-layout">
            <div class="ed-fields">
              <div class="field ed-span2">
                <label>Família *</label>
                <div class="ed-family-row">
                  <select id="eFamilia">
                    ${familias.map((f) => `<option value="${f.id}" ${f.id === familiaInicial ? "selected" : ""}>${UI.escapeHtml(f.nome)}</option>`).join("")}
                  </select>
                  <button class="btn btn--outline btn--sm" id="btnNovaFamiliaEditor" title="Criar família e seus atributos">+ Nova família</button>
                </div>
              </div>
              <div class="field">
                <label>Marca</label>
                <input id="eMarca" type="text" value="${UI.escapeHtml(produto ? produto.marca : "")}" placeholder="Ex.: Corfio">
              </div>
              <div class="field ed-span2">
                <label>Nome base do produto *</label>
                <input id="eNome" type="text" value="${UI.escapeHtml(produto ? produto.nome : "")}" placeholder="Ex.: Cabo Flexível 750V Antichama">
                <div class="nome-padrao">
                  <div class="nome-padrao-hint">
                    <span class="info-icone" title="Padrão de nomenclatura de fábrica (guia suave): o sistema sugere a estrutura e monta o nome, mas você pode ajustar livremente depois.">?</span>
                    <span id="ePadraoText">Padrão: <em>Item</em> + <em>Características</em> (bitola, tensão, CA) + <em>Marca</em>.</span>
                  </div>
                  <button class="btn btn--ghost btn--sm" id="btnMontarPadrao" type="button">Montar pelo padrão</button>
                </div>
              </div>
              <div class="field">
                <label>Categoria (opcional)</label>
                <input id="eCategoria" list="dlCategorias" type="text" value="${UI.escapeHtml(produto ? produto.categoria : "")}" placeholder="Fios e Cabos">
                <datalist id="dlCategorias">${categoriasSugestoes.map((c) => `<option value="${UI.escapeHtml(c)}">`).join("")}</datalist>
              </div>
              <div class="field">
                <label>Subcategoria (opcional)</label>
                <input id="eSubcategoria" list="dlSubcategorias" type="text" value="${UI.escapeHtml(produto ? produto.subcategoria : "")}" placeholder="Cabo Flexível">
                <datalist id="dlSubcategorias"></datalist>
              </div>
              <div class="field ed-span2">
                <label>Descrição (opcional)</label>
                <input id="eDesc" type="text" value="${UI.escapeHtml(produto ? produto.descricao : "")}" title="Descrição comercial do produto">
              </div>
              <div class="field ed-span2">
                <label>Termos de busca / sinônimos</label>
                <input id="eTermosBusca" type="text" value="${UI.escapeHtml(produto ? produto.termos_busca || "" : "")}" placeholder="Ex.: cabo, fio, 750V, antichama, barramento…">
                <p class="field-hint">Palavras-chave e variações do nome usado pelo mercado, para facilitar a busca (ex.: "fio" além de "cabo").</p>
              </div>
            </div>
            <aside class="ed-gestao">
              <div class="ed-gestao-head">Curva ABC &middot; Gestão de Linha</div>
              <div id="eAbcRecap" class="abc-recap"></div>
            </aside>
          </div>
        </div>

        <!-- Aba 2: Atributos da Família -->
        <div class="erp-panel hidden" id="tab-atributos">
          <p class="erp-panel-info">Combine os valores dos atributos da família selecionada. Os marcados ficam ativos na aba de variações.</p>
          <div id="eAtributos"></div>
        </div>

        <!-- Aba 3: Matriz de Variações (Data Grid comercial) -->
        <div class="erp-panel hidden" id="tab-variacoes">
          <div class="vt-toolbar">
            <button class="btn btn--accent btn--sm" id="btnGerar">Gerar Variações</button>
            <p id="eVariantesHint" class="vt-hint"></p>
          </div>
          <div class="vt-scroll">
            <div id="eVariantes" class="vt-grid-wrap"></div>
          </div>
          ${produto ? `
          <div class="vt-supplier">
            <div class="vt-supplier-head">
              <h4>Códigos por fornecedor</h4>
              <p style="margin:0;font-size:11px;color:var(--erp-ink-soft);">Código usado pelo fornecedor para cada variação, unidade de compra e fator de conversão (ex.: embalagem com 10 unidades &rarr; fator 10).</p>
            </div>
            <div class="vt-supplier-controls">
              <select id="fvFornecedor"><option value="">Selecione o fornecedor…</option></select>
              <button class="btn btn--accent btn--sm" id="btnSalvarFornecedor">Salvar códigos</button>
            </div>
            <div id="fvGrid" class="vt-supplier-grid"></div>
          </div>` : `
          <p class="vt-supplier-empty" style="margin-top:10px;">Salve o produto para cadastrar os códigos dos fornecedores por variação.</p>`}
        </div>

        <!-- Aba 4: Mídia e Anexos (Imagens) -->
        <div class="erp-panel hidden" id="tab-imagens">
          ${produto ? `
          <div class="img-tools">
            <label class="btn btn--ghost btn--sm">Enviar arquivos
              <input type="file" id="imgUpload" accept="image/*" multiple hidden>
            </label>
            <input id="imgUrl" type="text" placeholder="URL da página do produto ou imagem direta" style="flex:1;">
            <button class="btn btn--accent btn--sm" id="btnBaixarUrl">Baixar da internet</button>
          </div>
          <div id="imgGrid" class="img-grid"></div>` : `
          <p class="erp-empty">Salve o produto para poder adicionar imagens.</p>`}
        </div>

        <div class="form-actions">
          <button class="btn" id="btnCancelar">Cancelar</button>
          <button class="btn btn--accent" id="btnSalvar">Salvar produto</button>
        </div>
      </div>
    `;

    bindEditor($app, produto);
  }

  function carregarAtributosFamilia(familiaId, produto) {
    const f = familias.find((x) => x.id === familiaId);
    atributos = f ? (f.atributos || []) : [];
    if (produto && produto.atributos && produto.familia_id === familiaId) {
      atributos = produto.atributos;
    }
    // inicializa valores e variações
    valores = {};
    atributos.forEach((a) => { valores[a.id] = new Set(); });
    variantes = [];
    if (produto && produto.familia_id === familiaId) {
      (produto.variantes || []).forEach((v) => {
        const vals = {};
        atributos.forEach((a) => {
          const val = v.atributos ? v.atributos[String(a.id)] : undefined;
          if (val) { valores[a.id].add(val); vals[a.id] = val; }
        });
        variantes.push({ id: v.id, sku: v.sku || "", ean: v.ean || "", preco: v.preco || "", prom: v.preco_promocional || "", valores: vals });
      });
    }
  }

  function bindEditor($app, produto) {
    $app.querySelector("#btnVoltar").onclick = () => { location.hash = "#/produtos"; };
    $app.querySelector("#btnCancelar").onclick = () => { location.hash = "#/produtos"; };

    // ---- Navegação corporativa por abas (Folders) ----
    const $tabs = $app.querySelector(".erp-tabs");
    if ($tabs) {
      $tabs.addEventListener("click", (e) => {
        const tab = e.target.closest(".erp-tab");
        if (!tab) return;
        $app.querySelectorAll(".erp-tab").forEach((b) => b.classList.toggle("is-active", b === tab));
        $app.querySelectorAll(".erp-panel").forEach((p) => p.classList.add("hidden"));
        const panel = $app.querySelector("#tab-" + tab.dataset.tab);
        if (panel) panel.classList.remove("hidden");
      });
    }

    $app.querySelector("#eFamilia").addEventListener("change", (e) => {
      carregarAtributosFamilia(Number(e.target.value), null);
      renderAtributos($app);
      renderVariantes($app);
    });

    const $btnNovaFamilia = $app.querySelector("#btnNovaFamiliaEditor");
    if ($btnNovaFamilia) {
      $btnNovaFamilia.onclick = async () => {
        const saved = await abrirModalFamiliaForm(null);
        if (!saved) return;
        UI.closeModal();
        try { familias = await Api.listarFamilias(); } catch (e) { familias = []; }
        const alvo = (saved.id || Number($app.querySelector("#eFamilia").value));
        $app.querySelector("#eFamilia").innerHTML = familias.map((f) =>
          `<option value="${f.id}" ${f.id === alvo ? "selected" : ""}>${UI.escapeHtml(f.nome)}</option>`
        ).join("");
        const selecionada = familias.some((f) => f.id === alvo) ? alvo : (familias[0] ? familias[0].id : null);
        if (selecionada) {
          $app.querySelector("#eFamilia").value = String(selecionada);
          carregarAtributosFamilia(selecionada, null);
          renderAtributos($app);
          renderVariantes($app);
        }
      };
    }

    renderAtributos($app);
    renderVariantes($app);

    const $eCategoria = $app.querySelector("#eCategoria");
    if ($eCategoria) {
      atualizarSubsugestoes($eCategoria.value.trim());
      atualizarPadraoText($app);
      $eCategoria.addEventListener("input", () => {
        atualizarSubsugestoes($eCategoria.value.trim());
        atualizarPadraoText($app);
      });
    }

    const $btnMontarPadrao = $app.querySelector("#btnMontarPadrao");
    if ($btnMontarPadrao) {
      $btnMontarPadrao.onclick = () => montarNomePadrao($app);
    }

    if (produto) {
      bindFornecedor($app, produto);
    }

    const $abcRecap = $app.querySelector("#eAbcRecap");
    if ($abcRecap && produto) $abcRecap.innerHTML = abcRecapHtml(produto);

    $app.querySelector("#eVariantes").addEventListener("input", (e) => {
      const t = e.target;
      if (!t.dataset.field) return;
      const idx = Number(t.dataset.i);
      if (variantes[idx]) variantes[idx][t.dataset.field] = t.value;
    });

    $app.querySelector("#btnGerar").onclick = () => gerarVariacoes($app);

    $app.querySelector("#btnSalvar").onclick = () => salvar($app, produto);

    if (produto) {
      bindImagens($app, produto);
    }
  }

  // ---------------- atributos (chips + adicionar valor) ----------------

  // ---------- Padrão de nomenclatura de fábrica (guia suave) ----------

  const PADRAO_ATTRS = [
    "bitola", "tensao", "tensão", "capacidade", "potencia", "potência",
    "vazao", "vazão", "diametro", "diâmetro", "material", "cor",
    "espessura", "comprimento", "tamanho", "medida", "rolo", "voltagem",
  ];
  const CA_RE = /(^|[^a-z0-9])(n\s?[º°]?\s?ca|ca|certificado|aprovacao)([^a-z0-9]|$)/i;

  function normalize(str) {
    return String(str || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function ehAttrPadrao(nome) {
    const n = normalize(nome);
    if (CA_RE.test(nome)) return true;
    return PADRAO_ATTRS.some((k) => n.includes(k));
  }

  function atualizarPadraoText($app) {
    const $txt = $app.querySelector("#ePadraoText");
    if (!$txt) return;
    const cat = normalize($app.querySelector("#eCategoria").value.trim());
    let html = "Padrão: <em>Item</em> + <em>Características</em> (bitola, tensão, CA) + <em>Marca</em>.";
    if (cat.includes("epi")) {
      html = "Padrão EPI: <em>Item</em> + <em>Material/Tamanho</em> + <em>Nº CA</em> + <em>Marca</em>.";
    } else if (cat.includes("cabo") || cat.includes("fio")) {
      html = "Padrão de cabos: <em>Item</em> + <em>Bitola (mm²)</em> + <em>Tensão</em> + <em>Norma/Marca</em>.";
    }
    $txt.innerHTML = html;
  }

  function montarNomePadrao($app) {
    const base = $app.querySelector("#eNome").value.trim();
    const specs = atributos
      .filter((a) => ehAttrPadrao(a.nome))
      .map((a) => [...(valores[a.id] || [])].join("/"))
      .filter(Boolean);
    const marca = $app.querySelector("#eMarca").value.trim();
    const montado = [base, ...specs, marca].filter(Boolean).join(" ");
    $app.querySelector("#eNome").value = montado;
    if (!montado) {
      UI.toast("Informe o nome base ou selecione valores de atributos para montar.", "error");
    } else {
      UI.toast("Nome montado pelo padrão da família. Ajuste se necessário.", "success");
    }
  }

  // ---------------- códigos por fornecedor ----------------

  async function carregarFornecedores() {
    if (fornecedores.length) return;
    try { fornecedores = await Api.listarFornecedores(true); } catch (e) { fornecedores = []; }
  }

  function bindFornecedor($app, produto) {
    const $select = $app.querySelector("#fvFornecedor");
    if (!$select) return;
    carregarFornecedores().then(() => {
      $select.innerHTML = `<option value="">Selecione o fornecedor…</option>` +
        fornecedores.map((f) => `<option value="${f.id}">${UI.escapeHtml(f.nome)}</option>`).join("");
    });
    $select.addEventListener("change", () => renderFornecedor($app, produto));
    $app.querySelector("#btnSalvarFornecedor").onclick = () => salvarFornecedor($app, produto);
    renderFornecedor($app, produto);
  }

  function fornecedorMap(produto, fornecedorId) {
    const map = {};
    (produto.fornecedor_variantes || [])
      .filter((r) => r.fornecedor_id === fornecedorId)
      .forEach((r) => { map[r.variante_id] = r; });
    return map;
  }

  function renderFornecedor($app, produto) {
    const $grid = $app.querySelector("#fvGrid");
    const $select = $app.querySelector("#fvFornecedor");
    if (!$grid || !$select) return;
    const fornecedorId = Number($select.value);
    if (!fornecedorId) { $grid.innerHTML = ""; return; }
    const mapa = fornecedorMap(produto, fornecedorId);
    const rows = variantes.map((v, idx) => {
      const label = atributos.map((a) => v.valores[a.id]).filter(Boolean).join(" · ") || `Variação ${idx + 1}`;
      const key = `${fornecedorId}:${idx}`;
      const saved = mapa[v.id];
      fornecedorEdits[key] = fornecedorEdits[key] || {
        codigo: saved ? saved.codigo_fornecedor : "",
        unidade: saved ? saved.unidade_compra : "",
        fator: saved ? saved.fator_conversao : "",
        descricao: saved ? saved.descricao_fornecedor : "",
      };
      const e = fornecedorEdits[key];
      return `
        <tr>
          <td class="fv-variacao" title="${UI.escapeHtml(label)}">${UI.escapeHtml(label)}${v.sku ? ` <span style="color:var(--erp-ink-soft);font-weight:400;">· ${UI.escapeHtml(v.sku)}</span>` : ""}</td>
          <td><input type="text" data-k="${key}" data-f="codigo" placeholder="Código do fornecedor" value="${UI.escapeHtml(e.codigo)}"></td>
          <td><input type="text" data-k="${key}" data-f="unidade" placeholder="Ex.: CX, RL, PC" value="${UI.escapeHtml(e.unidade)}"></td>
          <td><input type="number" min="0" step="0.01" data-k="${key}" data-f="fator" placeholder="1" value="${UI.escapeHtml(e.fator !== "" && e.fator != null ? e.fator : "")}"></td>
        </tr>`;
    }).join("");
    if (!variantes.length) {
      $grid.innerHTML = `<p class="vt-supplier-empty">Gere as variações primeiro para associar os códigos.</p>`;
      return;
    }
    $grid.innerHTML = `
      <table class="vt-supplier-table">
        <thead><tr><th class="fv-c-variacao">Variação</th><th>Código do fornecedor</th><th>Unid. compra</th><th>Fator conv.</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    $grid.querySelectorAll("input[data-k]").forEach((i) => {
      i.oninput = () => { fornecedorEdits[i.dataset.k] = fornecedorEdits[i.dataset.k] || {}; fornecedorEdits[i.dataset.k][i.dataset.f] = i.value; };
    });
  }

  async function salvarFornecedor($app, produto) {
    const fornecedorId = Number($app.querySelector("#fvFornecedor").value);
    if (!fornecedorId) { UI.toast("Selecione o fornecedor", "error"); return; }
    const itens = variantes.map((v, idx) => {
      const e = fornecedorEdits[`${fornecedorId}:${idx}`] || {};
      return {
        variante_id: v.id,
        codigo_fornecedor: e.codigo || "",
        descricao_fornecedor: e.descricao || "",
        unidade_compra: e.unidade || "",
        fator_conversao: e.fator !== "" && e.fator != null ? Number(e.fator) : 1,
      };
    });
    try {
      const res = await Api.salvarFornecedorVariantes(produto.id, fornecedorId, itens);
      produto.fornecedor_variantes = res.mapping;
      UI.toast(`Códigos salvos para ${fornecedores.find((f) => f.id === fornecedorId)?.nome || "o fornecedor"}`, "success");
      renderFornecedor($app, produto);
    } catch (e) {
      UI.toast("Erro ao salvar códigos: " + e.message, "error");
    }
  }

  function renderAtributos($app) {
    const $wrap = $app.querySelector("#eAtributos");
    if (!atributos.length) {
      $wrap.innerHTML = `<p style="font-size:13px;color:var(--ink-soft);">Essa família não tem atributos. Edite a família para adicioná-los.</p>`;
      return;
    }
    $wrap.innerHTML = atributos.map(attrBlockHtml).join("");
    $wrap.querySelectorAll(".chip input").forEach((i) => {
      i.onchange = (ev) => {
        const set = valores[Number(ev.target.dataset.attr)];
        if (ev.target.checked) set.add(ev.target.value); else set.delete(ev.target.value);
        renderAtributos($app);
      };
    });
    $wrap.querySelectorAll(".attr-add button").forEach((b) => {
      b.onclick = () => {
        const input = b.parentElement.querySelector("input");
        const attrId = Number(input.dataset.attr);
        const val = input.value.trim();
        if (!val) return;
        valores[attrId].add(val);
        input.value = "";
        renderAtributos($app);
      };
    });
    $wrap.querySelectorAll(".attr-add input").forEach((i) => {
      i.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const val = i.value.trim();
          if (!val) return;
          valores[Number(i.dataset.attr)].add(val);
          i.value = "";
          renderAtributos($app);
        }
      });
    });
  }

  function attrBlockHtml(a) {
    const set = valores[a.id];
    const opts = a.tipo === "lista" ? [...a.opcoes] : [];
    const custom = [...set].filter((v) => !opts.includes(v));
    const display = [...opts, ...custom];
    const marker = (v) => `<span class="chip-check" aria-hidden="true">${set.has(v) ? "✓" : ""}</span>`;
    const titular = () => `
      <span class="attr-title attr-title-obr">${UI.escapeHtml(a.nome)}
        ${a.obrigatorio ? `<span class="obr-badge" title="Atributo obrigatório para produtos desta família">* obrigatório</span>` : ""}
      </span>`;
    if (!display.length && a.tipo === "livre") {
      return `
        <div class="attr-block ${a.obrigatorio ? "has-obrigatorio" : ""}">
          <div class="attr-head">${titular()}</div>
          <div class="attr-add">
            <input type="text" data-attr="${a.id}" placeholder="Digite o valor e pressione Enter…">
            <button type="button" class="btn btn--ghost btn--sm">Adicionar</button>
          </div>
        </div>`;
    }
    return `
      <div class="attr-block ${a.obrigatorio ? "has-obrigatorio" : ""}">
        <div class="attr-head">${titular()}</div>
        <div class="chip-group">${display.map((v) => `
          <label class="chip ${set.has(v) ? "is-on" : ""}">
            <input type="checkbox" data-attr="${a.id}" value="${UI.escapeHtml(v)}" ${set.has(v) ? "checked" : ""}>
            ${marker(v)}${UI.escapeHtml(v)}
          </label>`).join("")}
        </div>
        <div class="attr-add">
          <input type="text" data-attr="${a.id}" placeholder="Adicionar valor…">
          <button type="button" class="btn btn--ghost btn--sm">Adicionar</button>
        </div>
      </div>`;
  }

  // ---------------- variações (combinações) ----------------

  function gerarVariacoes($app) {
    const keys = atributos.map((a) => a.id);
    const vazios = atributos.filter((a) => !valores[a.id] || valores[a.id].size === 0);
    if (vazios.length) {
      UI.toast(`Selecione ao menos um valor para: ${vazios.map((a) => a.nome).join(", ")}`, "error");
      return;
    }
    const arrays = keys.map((k) => [...valores[k]]);
    const combos = cartesiano(arrays);
    const existentes = {};
    variantes.forEach((v) => { existentes[JSON.stringify(v.valores)] = v; });
    variantes = combos.map((vals) => {
      const attr = {};
      keys.forEach((k, j) => { attr[k] = vals[j]; });
      const prev = existentes[JSON.stringify(attr)];
      return {
        id: prev ? prev.id : undefined,
        sku: prev ? prev.sku : "",
        ean: prev ? prev.ean : "",
        preco: prev ? prev.preco : "",
        prom: prev ? prev.prom : "",
        valores: attr,
      };
    });
    renderVariantes($app);
    UI.toast(`${variantes.length} variação(ões) gerada(s)`, "success");
  }

  function cartesiano(arrays) {
    return arrays.reduce((acc, cur) => acc.flatMap((a) => cur.map((c) => [...a, c])), [[]]);
  }

  function renderVariantes($app) {
    const $wrap = $app.querySelector("#eVariantes");
    const $hint = $app.querySelector("#eVariantesHint");
    if (!atributos.length) {
      if ($hint) $hint.textContent = "";
      $wrap.innerHTML = `<p class="erp-empty">Selecione uma família com atributos para gerar variações.</p>`;
      return;
    }
    if (!variantes.length) {
      if ($hint) $hint.textContent = "Selecione os valores dos atributos e clique em \u201CGerar Variações\u201D.";
      $wrap.innerHTML = "";
      return;
    }
    if ($hint) $hint.textContent = `${variantes.length} variação(ões) · atributos: ${atributos.map((a) => a.nome).join(" · ")}. Edite diretamente nas células (SKU, EAN, Preço, Promo).`;
    const rows = variantes.map((v, idx) => {
      const label = atributos.map((a) => v.valores[a.id]).filter(Boolean).join(" · ") || "—";
      return `
      <tr class="${idx % 2 ? "is-zebra" : ""}">
        <td class="vt-variacao" title="${UI.escapeHtml(label)}">${UI.escapeHtml(label)}</td>
        <td><input data-i="${idx}" data-field="sku" type="text" placeholder="SKU" value="${UI.escapeHtml(v.sku)}"></td>
        <td><input data-i="${idx}" data-field="ean" type="text" placeholder="EAN" value="${UI.escapeHtml(v.ean)}"></td>
        <td><input data-i="${idx}" data-field="preco" type="number" min="0" step="0.01" placeholder="R$" value="${UI.escapeHtml(v.preco !== "" && v.preco != null ? v.preco : "")}"></td>
        <td><input data-i="${idx}" data-field="prom" type="number" min="0" step="0.01" placeholder="Promo" value="${UI.escapeHtml(v.prom != null ? v.prom : "")}"></td>
        <td class="vt-del"><button type="button" class="icon-btn" data-rm="${idx}" title="Remover variação">×</button></td>
      </tr>`;
    }).join("");
    $wrap.innerHTML = `
      <table class="vt-grid">
        <thead>
          <tr><th class="vt-c-variacao">Variação</th><th>SKU</th><th>EAN</th><th>Preço</th><th>Promo.</th><th class="vt-c-del"></th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;

    $wrap.querySelectorAll("[data-rm]").forEach((b) => {
      b.onclick = () => { variantes.splice(Number(b.dataset.rm), 1); renderVariantes($app); };
    });
  }

  // ---------------- salvar ----------------

  function abcRecapHtml(p) {
    const chips = (nome, val, cor) => val
      ? `<span class="abc-chip" style="background:${cor};color:#fff;">${UI.escapeHtml(nome)}: <strong>${UI.escapeHtml(String(val))}</strong></span>`
      : "";
    const classe = p.classe_abc || "—";
    const corClasse = classe === "A" ? "#2f6df6" : classe === "B" ? "#e8a000" : classe === "C" ? "#9aa4b2" : "transparent";
    const emLinha = p.em_linha == null ? "" : (p.em_linha ? "No rolar" : "Fora do rolar");
    const corLinha = p.em_linha == null ? "" : (p.em_linha ? "#1c9d74" : "#d04848");
    return `
      <div style="display:flex;flex-wrap:wrap;gap:8px;">
        <span class="abc-chip" style="background:${corClasse};color:#fff;${classe === "—" ? "background:#e7ebf0;color:#667;" : ""}">Classe: <strong>${UI.escapeHtml(String(classe))}</strong></span>
        ${emLinha !== "" ? `<span class="abc-chip" style="background:${corLinha};color:#fff;">${emLinha}</span>` : ""}
        ${chips("Linha", p.linha_produto, "#5b6472")}
        ${chips("Margem", (p.margem_lucro_estimada != null ? (p.margem_lucro_estimada * 100).toFixed(0) + "%" : ""), "#8a5bd8")}
        ${chips("Giro", p.giro_esperado_mercado != null ? p.giro_esperado_mercado.toFixed(2) : "", "#0f7bd8")}
        ${chips("Valor", p.valor_agregado, "#0f87a8")}
        ${chips("Lucro est.", p.lucro_total_estimado != null ? UI.fmtMoney(p.lucro_total_estimado) : "", "#1c9d74")}
      </div>`;
  }

  async function salvar($app, produto) {
    const familia_id = Number($app.querySelector("#eFamilia").value);
    const nome = $app.querySelector("#eNome").value.trim();
    if (!familia_id) { UI.toast("Selecione a família", "error"); return; }
    if (!nome) { UI.toast("Informe o nome base do produto", "error"); return; }

    // -- validações de atributos obrigatórios + CA (EPI) --
    const semsValor = atributos.filter(
      (a) => a.obrigatorio && (!valores[a.id] || valores[a.id].size === 0)
    );
    if (semsValor.length) {
      UI.toast("Preencha os atributos obrigatórios: " + semsValor.map((a) => a.nome).join(", "), "error");
      $app.querySelector(".erp-tab[data-tab=\"atributos\"]").click();
      return;
    }
    const caAttrs = atributos.filter((a) => CA_RE.test(a.nome));
    for (const a of caAttrs) {
      for (const v of (valores[a.id] || [])) {
        if (!/^[\d.\s]+$/.test(String(v).trim())) {
          UI.toast(`O atributo "${a.nome}" deve ser um número de CA válido (ex.: 12345 ou 12.345).`, "error");
          $app.querySelector(".erp-tab[data-tab=\"atributos\"]").click();
          return;
        }
      }
    }

    const payload = {
      familia_id,
      nome,
      marca: $app.querySelector("#eMarca").value.trim(),
      descricao: $app.querySelector("#eDesc").value.trim(),
      termos_busca: $app.querySelector("#eTermosBusca").value.trim(),
      categoria: $app.querySelector("#eCategoria").value.trim(),
      subcategoria: $app.querySelector("#eSubcategoria").value.trim(),
      variantes: variantes.map((v) => ({
        id: v.id,
        sku: v.sku || "",
        ean: v.ean || "",
        preco: v.preco !== "" && v.preco != null ? Number(v.preco) : 0,
        preco_promocional: v.prom !== "" && v.prom != null ? Number(v.prom) : null,
        observacao: "",
        atributos: v.valores,
      })),
    };
    try {
      let id = produto ? produto.id : null;
      if (produto) await Api.atualizarProdutoCadastro(produto.id, payload);
      else { const res = await Api.criarProdutoCadastro(payload); id = res.id; }
      UI.toast("Produto salvo", "success");
      if (produto) {
        location.hash = `#/produtos/${produto.id}`;
      } else {
        location.hash = `#/produtos/${id}`;
      }
    } catch (e) {
      UI.toast("Erro ao salvar: " + e.message, "error");
    }
  }

  // ---------------- imagens ----------------

  function bindImagens($app, produto) {
    const renderImagens = () => {
      const $grid = $app.querySelector("#imgGrid");
      if (!$grid) return;
      const imgs = produto.imagens || [];
      if (!imgs.length) {
        $grid.innerHTML = `<p style="font-size:13px;color:var(--ink-soft);">Nenhuma imagem. Envie arquivos ou informe a URL de uma página do produto.</p>`;
        return;
      }
      $grid.innerHTML = imgs.map((im, i) => `
        <div class="img-cell ${i === 0 ? "is-capa" : ""}">
          <img src="${UI.escapeHtml(im.url)}" loading="lazy" alt="">
          ${i === 0 ? `<span class="img-capa-badge">Capa</span>` : ""}
          ${i > 0 ? `<button class="img-capa-btn" data-capa="${im.id}" title="Definir como imagem de capa">★</button>` : ""}
          <button class="img-remove" data-img="${im.id}" title="Excluir imagem">×</button>
        </div>`).join("");
      $grid.querySelectorAll(".img-remove").forEach((b) => {
        b.onclick = async () => {
          try {
            await Api.excluirImagem(Number(b.dataset.img));
            produto.imagens = (produto.imagens || []).filter((x) => x.id !== Number(b.dataset.img));
            renderImagens();
          } catch (e) { UI.toast("Erro ao excluir imagem: " + e.message, "error"); }
        };
      });
      $grid.querySelectorAll(".img-capa-btn").forEach((b) => {
        b.onclick = async () => {
          const $btn = b;
          $btn.disabled = true;
          try {
            await Api.definirCapaImagem(produto.id, Number(b.dataset.capa));
            produto = await Api.detalharProdutoCadastro(produto.id);
            renderImagens();
            UI.toast("Imagem de capa atualizada", "success");
          } catch (e) {
            UI.toast("Erro ao definir capa: " + e.message, "error");
          } finally {
            $btn.disabled = false;
          }
        };
      });
    };

    $app.querySelector("#imgUpload").addEventListener("change", async (e) => {
      const files = e.target.files;
      if (!files.length) return;
      const fd = new FormData();
      for (const f of files) fd.append("files", f);
      try {
        await Api.enviarImagensProduto(produto.id, fd);
        produto = await Api.detalharProdutoCadastro(produto.id);
        renderImagens();
        UI.toast(`${files.length} imagem(ns) enviada(s)`, "success");
      } catch (err) {
        UI.toast("Erro no upload: " + err.message, "error");
      }
      e.target.value = "";
    });

    $app.querySelector("#btnBaixarUrl").onclick = async () => {
      const url = $app.querySelector("#imgUrl").value.trim();
      if (!url) { UI.toast("Informe a URL", "error"); return; }
      const $btn = $app.querySelector("#btnBaixarUrl");
      $btn.disabled = true;
      $btn.textContent = "Baixando…";
      try {
        const res = await Api.baixarImagensUrl(produto.id, url);
        produto = await Api.detalharProdutoCadastro(produto.id);
        renderImagens();
        UI.toast(`${res.total} imagem(ns) baixada(s)`, "success");
        if (res.erros && res.erros.length) {
          UI.toast(`Erros: ${res.erros.slice(0, 3).join(" | ")}`, "error");
        }
      } catch (err) {
        UI.toast("Erro ao baixar: " + err.message, "error");
      } finally {
        $btn.disabled = false;
        $btn.textContent = "Baixar da internet";
      }
    };

    renderImagens();
  }

  // ===================================================================

  return { renderLista, renderEditor };
})();
