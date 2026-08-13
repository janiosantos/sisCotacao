import { api, type Cliente, type ClienteContato, type ClienteEndereco, type ClientePayload, type Vendedor } from "../api/client";
import { escapeHtml } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando clientes…</div>`;
  let clientes: Cliente[] = [];
  let vendedores: Vendedor[] = [];
  try {
    const [c, ctx] = await Promise.all([api.listarClientes(), api.contextoCliente()]);
    clientes = c;
    vendedores = ctx.vendedores;
  } catch (e) {
    toast("Erro ao carregar clientes: " + (e as Error).message, "error");
  }
  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Clientes</h1>
        <p class="page-sub">Cadastro completo: dados, endereços, contatos, apoio comercial e fiscal.</p>
      </div>
      <button class="btn btn--accent" id="btnNovo">+ Novo cliente</button>
    </div>
    <div id="tabelaWrap"></div>
  `;
  const $t = $app.querySelector<HTMLElement>("#tabelaWrap")!;
  $t.innerHTML = tabela(clientes);
  $app.querySelector<HTMLButtonElement>("#btnNovo")!.addEventListener("click", () => abrirModal($app, null, vendedores));
  $app.querySelectorAll<HTMLElement>("[data-edit]").forEach((b) => {
    b.addEventListener("click", () => {
      const c = clientes.find((x) => x.id === Number(b.dataset.edit))!;
      abrirModal($app, c, vendedores);
    });
  });
  $app.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
    b.addEventListener("click", async () => {
      const c = clientes.find((x) => x.id === Number(b.dataset.toggle))!;
      await api.alternarAtivoCliente(c.id, !c.ativo);
      await render($app);
    });
  });
}

function tabela(clientes: Cliente[]): string {
  if (!clientes.length) return `<div class="empty-box"><p>Nenhum cliente cadastrado</p></div>`;
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Nome</th><th>Documento</th><th>E-mail</th><th>Vendedor</th><th>Limite</th><th>Status</th><th></th></tr></thead>
        <tbody>
          ${clientes.map((c) => `
            <tr>
              <td>${escapeHtml(c.nome)}</td>
              <td style="font-family:var(--font-mono);font-size:12.5px;">${escapeHtml(c.doc || "—")}</td>
              <td style="font-size:12.5px;">${escapeHtml(c.email || "—")}</td>
              <td style="font-size:12.5px;">${escapeHtml(c.vendedor_nome || "—")}</td>
              <td>${c.limite_credito ? `R$ ${c.limite_credito.toFixed(2)}` : "—"}</td>
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

// ──────────────────────────────────────────────────────────
//  Modal com abas
// ──────────────────────────────────────────────────────────

async function abrirModal($app: HTMLElement, cliente: Cliente | null, vendedores: Vendedor[]): Promise<void> {
  const isEdit = !!cliente;
  let aba = "dados";
  let enderecos: ClienteEndereco[] = [];
  let contatos: ClienteContato[] = [];

  if (isEdit && cliente) {
    try {
      [enderecos, contatos] = await Promise.all([
        api.listarEnderecosCliente(cliente.id),
        api.listarContatosCliente(cliente.id),
      ]);
    } catch { /* */ }
  }

  const tabBar = (a: string) => `
    <div class="tab-bar" style="margin-bottom:12px;">
      <button class="tab-btn ${a === "dados" ? "is-active" : ""}" data-aba="dados">Dados</button>
      <button class="tab-btn ${a === "enderecos" ? "is-active" : ""}" data-aba="enderecos">Endereços (${enderecos.length})</button>
      <button class="tab-btn ${a === "contatos" ? "is-active" : ""}" data-aba="contatos">Contatos (${contatos.length})</button>
      <button class="tab-btn ${a === "comercial" ? "is-active" : ""}" data-aba="comercial">Apoio Comercial</button>
      <button class="tab-btn ${a === "fiscal" ? "is-active" : ""}" data-aba="fiscal">Apoio Fiscal</button>
    </div>`;

  const content = (a: string) => {
    if (a === "dados") return `
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div class="field"><label>Nome *</label><input id="mNome" value="${escapeHtml(cliente?.nome || "")}"></div>
        <div class="field"><label>CPF/CNPJ</label><input id="mDoc" value="${escapeHtml(cliente?.doc || "")}"></div>
        <div style="display:flex;gap:10px;">
          <div class="field" style="flex:1;"><label>Condição de contribuinte</label>
            <select id="mContribuinte">
              <option value="">Não definido</option>
              <option value="contribuinte" ${cliente?.contribuinte === "contribuinte" ? "selected" : ""}>Contribuinte ICMS</option>
              <option value="nao_contribuinte" ${cliente?.contribuinte === "nao_contribuinte" ? "selected" : ""}>Não contribuinte</option>
            </select>
          </div>
          <div class="field" style="flex:1;"><label>Inscrição Estadual</label><input id="mIe" value="${escapeHtml(cliente?.ie || "")}" autocomplete="off"></div>
        </div>
        <div style="display:flex;gap:10px;">
          <div class="field" style="flex:1;"><label>E-mail</label><input id="mEmail" value="${escapeHtml(cliente?.email || "")}"></div>
          <div class="field" style="flex:1;"><label>WhatsApp</label><input id="mWhats" value="${escapeHtml(cliente?.whatsapp || "")}"></div>
        </div>
        <div class="field"><label>Vendedor</label>
          <select id="mVendedor"><option value="">—</option>
            ${vendedores.map((v) => `<option value="${v.id}" ${cliente?.vendedor_id === v.id ? "selected" : ""}>${escapeHtml(v.nome)}</option>`).join("")}
          </select>
        </div>
        <div class="field"><label>Limite de crédito (R$)</label><input id="mLimite" type="number" min="0" step="0.01" value="${cliente?.limite_credito ?? ""}"></div>
        <div class="field"><label>Observações</label><textarea id="mObs">${escapeHtml(cliente?.observacoes || "")}</textarea></div>
      </div>`;
    if (a === "enderecos") return `
      <div style="margin-bottom:8px;"><button class="btn btn--sm btn--accent" id="btnNovoEnd">+ Endereço</button></div>
        <div id="endList">${enderecos.length ? enderecos.map((e) => `
        <div class="estq-filtros" style="border:1px solid var(--line);border-radius:8px;padding:8px;margin-bottom:6px;">
          <span><strong>${e.tipo}</strong>: ${escapeHtml(e.logradouro)}, ${escapeHtml(e.numero)}${e.bairro ? " - " + escapeHtml(e.bairro) : ""}${e.cidade ? " - " + escapeHtml(e.cidade) : ""}</span>
          <button class="btn btn--ghost btn--sm" data-exc-end="${e.id}">×</button>
        </div>`).join("") : `<p class="pdv-sem-res">Nenhum endereço cadastrado</p>`}</div>`;
    if (a === "contatos") return `
      <div style="margin-bottom:8px;"><button class="btn btn--sm btn--accent" id="btnNovoCtt">+ Contato</button></div>
      <div id="cttList">${contatos.length ? contatos.map((c) => `
        <div class="estq-filtros" style="border:1px solid var(--line);border-radius:8px;padding:8px;margin-bottom:6px;">
          <span><strong>${escapeHtml(c.nome)}</strong>${c.cargo ? " (" + escapeHtml(c.cargo) + ")" : ""}${c.telefone ? " - " + escapeHtml(c.telefone) : ""}</span>
          <button class="btn btn--ghost btn--sm" data-exc-ctt="${c.id}">×</button>
        </div>`).join("") : `<p class="pdv-sem-res">Nenhum contato cadastrado</p>`}</div>`;
    if (a === "comercial") return `<div id="apoioComercialForm"><p class="pdv-sem-res">Carregando…</p></div>`;
    if (a === "fiscal") return `<div id="apoioFiscalForm"><p class="pdv-sem-res">Carregando…</p></div>`;
    return "";
  };

  const modal = openModal(
    `<div class="modal-head"><h3>${isEdit ? "Editar" : "Novo"} cliente</h3><button class="icon-btn" data-close>×</button></div>
     ${tabBar(aba)}
     <div id="cliModalBody">${content(aba)}</div>
     <div class="modal-actions">
       <button class="btn" data-close>Cancelar</button>
       <button class="btn btn--accent" id="btnSalvar">Salvar</button>
     </div>`,
    { modalClass: "modal--wide" },
  );

  const $body = modal.querySelector<HTMLElement>("#cliModalBody")!;

  modal.querySelectorAll<HTMLElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      aba = btn.dataset.aba || "dados";
      modal.querySelector(".modal-head")!.insertAdjacentHTML("afterend", tabBar(aba));
      modal.querySelectorAll(".tab-btn").forEach((b) => b.remove());
      $body.innerHTML = content(aba);
      if (aba === "comercial" && cliente) carregarApoioComercial(modal, cliente.id);
      if (aba === "fiscal" && cliente) carregarApoioFiscal(modal, cliente.id);
      bindEndCtt(modal, cliente, enderecos, contatos);
    });
  });

  if (cliente) {
    if (aba === "comercial") await carregarApoioComercial(modal, cliente.id);
    if (aba === "fiscal") await carregarApoioFiscal(modal, cliente.id);
  }
  bindEndCtt(modal, cliente, enderecos, contatos);

  modal.querySelector<HTMLButtonElement>("#btnSalvar")!.onclick = async () => {
    const nome = modal.querySelector<HTMLInputElement>("#mNome")?.value.trim();
    if (!nome) { toast("Informe o nome do cliente", "error"); return; }
    const payload: ClientePayload = {
      nome, doc: modal.querySelector<HTMLInputElement>("#mDoc")?.value.trim() || null,
      email: modal.querySelector<HTMLInputElement>("#mEmail")?.value.trim() || null,
      whatsapp: modal.querySelector<HTMLInputElement>("#mWhats")?.value.trim() || null,
      vendedor_id: Number(modal.querySelector<HTMLSelectElement>("#mVendedor")?.value) || null,
      limite_credito: Number(modal.querySelector<HTMLInputElement>("#mLimite")?.value) || 0,
      observacoes: modal.querySelector<HTMLTextAreaElement>("#mObs")?.value.trim() || null,
      contribuinte: modal.querySelector<HTMLSelectElement>("#mContribuinte")?.value || undefined,
      ie: modal.querySelector<HTMLInputElement>("#mIe")?.value.trim() || undefined,
    };
    try {
      if (isEdit && cliente) await api.atualizarCliente(cliente.id, payload);
      else await api.criarCliente(payload);
      closeModal();
      toast("Cliente salvo", "success");
      await render($app);
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };
}

function bindEndCtt(modal: HTMLElement, cliente: Cliente | null, _enderecos: ClienteEndereco[], _contatos: ClienteContato[]): void {
  if (!cliente) return;
  modal.querySelector<HTMLElement>("#btnNovoEnd")?.addEventListener("click", () => {
    openModal(
      `<div class="modal-head"><h3>Novo endereço</h3><button class="icon-btn" data-close>×</button></div>
       <div style="display:flex;flex-direction:column;gap:10px;">
         <div class="field"><label>Tipo</label>
           <select id="endTipo"><option value="cobranca">Cobrança</option><option value="entrega">Entrega</option><option value="faturamento">Faturamento</option></select></div>
         <div class="field"><label>CEP</label><input id="endCep" maxlength="9"></div>
         <div class="field"><label>Logradouro</label><input id="endLog"></div>
         <div style="display:flex;gap:10px;">
           <div class="field" style="flex:0.3"><label>Número</label><input id="endNum"></div>
           <div class="field" style="flex:1"><label>Complemento</label><input id="endComp"></div>
         </div>
         <div class="field"><label>Bairro</label><input id="endBairro"></div>
         <div style="display:flex;gap:10px;">
           <div class="field" style="flex:1"><label>Cidade</label><input id="endCid"></div>
           <div class="field" style="flex:0.3"><label>UF</label><input id="endUf" maxlength="2"></div>
         </div>
       </div>
       <div class="modal-actions"><button class="btn btn--accent" id="endSalvar">Salvar</button><button class="btn" data-close>Cancelar</button></div>`,
      {
        onMount(m) {
          m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
          m.querySelector<HTMLElement>("#endSalvar")!.onclick = async () => {
            try {
              await api.criarEnderecoCliente(cliente.id, {
                tipo: m.querySelector<HTMLSelectElement>("#endTipo")!.value,
                cep: m.querySelector<HTMLInputElement>("#endCep")?.value || "",
                logradouro: m.querySelector<HTMLInputElement>("#endLog")?.value || "",
                numero: m.querySelector<HTMLInputElement>("#endNum")?.value || "",
                complemento: m.querySelector<HTMLInputElement>("#endComp")?.value || "",
                bairro: m.querySelector<HTMLInputElement>("#endBairro")?.value || "",
                cidade: m.querySelector<HTMLInputElement>("#endCid")?.value || "",
                uf: m.querySelector<HTMLInputElement>("#endUf")?.value || "",
              });
              toast("Endereço adicionado", "success");
              closeModal();
              location.reload();
            } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
          };
        },
      }
    );
  });
  modal.querySelectorAll<HTMLElement>("[data-exc-end]").forEach((b) => {
    b.addEventListener("click", async () => {
      await api.excluirEnderecoCliente(Number(b.dataset.excEnd));
      location.reload();
    });
  });
  modal.querySelector<HTMLElement>("#btnNovoCtt")?.addEventListener("click", () => {
    openModal(
      `<div class="modal-head"><h3>Novo contato</h3><button class="icon-btn" data-close>×</button></div>
       <div style="display:flex;flex-direction:column;gap:10px;">
         <div class="field"><label>Nome *</label><input id="cttNome"></div>
         <div class="field"><label>Cargo</label><input id="cttCargo"></div>
         <div style="display:flex;gap:10px;">
           <div class="field" style="flex:1"><label>Telefone</label><input id="cttTel"></div>
           <div class="field" style="flex:1"><label>E-mail</label><input id="cttEmail"></div>
         </div>
       </div>
       <div class="modal-actions"><button class="btn btn--accent" id="cttSalvar">Salvar</button><button class="btn" data-close>Cancelar</button></div>`,
      {
        onMount(m) {
          m.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
          m.querySelector<HTMLElement>("#cttSalvar")!.onclick = async () => {
            const nome = m.querySelector<HTMLInputElement>("#cttNome")?.value.trim();
            if (!nome) { toast("Informe o nome", "error"); return; }
            try {
              await api.criarContatoCliente(cliente.id, {
                nome, cargo: m.querySelector<HTMLInputElement>("#cttCargo")?.value || "",
                telefone: m.querySelector<HTMLInputElement>("#cttTel")?.value || "",
                email: m.querySelector<HTMLInputElement>("#cttEmail")?.value || "",
              });
              toast("Contato adicionado", "success");
              closeModal();
              location.reload();
            } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
          };
        },
      }
    );
  });
  modal.querySelectorAll<HTMLElement>("[data-exc-ctt]").forEach((b) => {
    b.addEventListener("click", async () => {
      await api.excluirContatoCliente(Number(b.dataset.excCtt));
      location.reload();
    });
  });
}

async function carregarApoioComercial(modal: HTMLElement, clienteId: number): Promise<void> {
  const $form = modal.querySelector<HTMLElement>("#apoioComercialForm");
  if (!$form) return;
  let data: Record<string, unknown> = {};
  try { data = await api.getApoioComercial(clienteId) as unknown as Record<string, unknown>; } catch { /* */ }
  $form.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div class="field"><label>Tabela de Preço (ID)</label><input id="acTabela" type="number" value="${data.tabela_preco_id || ""}"></div>
      <div class="field"><label>Condição de Pagamento (ID)</label><input id="acCond" type="number" value="${data.condicao_pagamento_id || ""}"></div>
      <div class="field"><label>Limite de Crédito (R$)</label><input id="acLimite" type="number" step="0.01" value="${data.limite_credito || 0}"></div>
      <div class="field"><label>Transportadora</label><input id="acTransp" value="${data.transportadora || ""}"></div>
      <button class="btn btn--accent" id="acSalvar">Salvar</button>
    </div>`;
  $form.querySelector<HTMLElement>("#acSalvar")!.onclick = async () => {
    try {
      await api.upsertApoioComercial(clienteId, {
        tabela_preco_id: Number($form.querySelector<HTMLInputElement>("#acTabela")?.value) || null,
        condicao_pagamento_id: Number($form.querySelector<HTMLInputElement>("#acCond")?.value) || null,
        limite_credito: Number($form.querySelector<HTMLInputElement>("#acLimite")?.value) || 0,
        transportadora: $form.querySelector<HTMLInputElement>("#acTransp")?.value || "",
      });
      toast("Apoio comercial salvo", "success");
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };
}

async function carregarApoioFiscal(modal: HTMLElement, clienteId: number): Promise<void> {
  const $form = modal.querySelector<HTMLElement>("#apoioFiscalForm");
  if (!$form) return;
  let data: Record<string, unknown> = {};
  try { data = await api.getApoioFiscal(clienteId) as unknown as Record<string, unknown>; } catch { /* */ }
  $form.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div class="field"><label>CFOP Padrão</label><input id="afCfop" value="${data.cfop_padrao || ""}"></div>
      <div style="display:flex;gap:10px;">
        <div class="field" style="flex:1"><label>CST ICMS</label><input id="afCstIcms" value="${data.cst_icms || ""}"></div>
        <div class="field" style="flex:1"><label>Alíq. ICMS %</label><input id="afIcms" type="number" step="0.01" value="${data.aliquota_icms || 0}"></div>
      </div>
      <div style="display:flex;gap:10px;">
        <div class="field" style="flex:1"><label>CST PIS</label><input id="afCstPis" value="${data.cst_pis || ""}"></div>
        <div class="field" style="flex:1"><label>Alíq. PIS %</label><input id="afPis" type="number" step="0.01" value="${data.aliquota_pis || 0}"></div>
      </div>
      <div style="display:flex;gap:10px;">
        <div class="field" style="flex:1"><label>CST COFINS</label><input id="afCstCofins" value="${data.cst_cofins || ""}"></div>
        <div class="field" style="flex:1"><label>Alíq. COFINS %</label><input id="afCofins" type="number" step="0.01" value="${data.aliquota_cofins || 0}"></div>
      </div>
      <button class="btn btn--accent" id="afSalvar">Salvar</button>
    </div>`;
  $form.querySelector<HTMLElement>("#afSalvar")!.onclick = async () => {
    try {
      await api.upsertApoioFiscal(clienteId, {
        cfop_padrao: $form.querySelector<HTMLInputElement>("#afCfop")?.value || "",
        cst_icms: $form.querySelector<HTMLInputElement>("#afCstIcms")?.value || "",
        cst_pis: $form.querySelector<HTMLInputElement>("#afCstPis")?.value || "",
        cst_cofins: $form.querySelector<HTMLInputElement>("#afCstCofins")?.value || "",
        aliquota_icms: Number($form.querySelector<HTMLInputElement>("#afIcms")?.value) || 0,
        aliquota_pis: Number($form.querySelector<HTMLInputElement>("#afPis")?.value) || 0,
        aliquota_cofins: Number($form.querySelector<HTMLInputElement>("#afCofins")?.value) || 0,
      });
      toast("Apoio fiscal salvo", "success");
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };
}
