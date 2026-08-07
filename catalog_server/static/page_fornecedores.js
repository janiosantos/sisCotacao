// page_fornecedores.js — cadastro de fornecedores.
const PageFornecedores = (() => {
  async function render($app) {
    $app.innerHTML = `<div class="loading">Carregando fornecedores…</div>`;
    let fornecedores = [];
    try {
      fornecedores = await Api.listarFornecedores();
    } catch (e) {
      UI.toast("Erro ao carregar fornecedores: " + e.message, "error");
    }

    $app.innerHTML = `
      <div class="page-head">
        <div>
          <h1 class="page-title">Fornecedores</h1>
          <p class="page-sub">Cadastro usado para convidar fornecedores nas cotações.</p>
        </div>
        <button class="btn btn--accent" id="btnNovo">+ Novo fornecedor</button>
      </div>

      ${fornecedores.length === 0 ? `<div class="empty-box"><p>Nenhum fornecedor cadastrado</p><p>Cadastre o primeiro para começar a enviar cotações.</p></div>` : listTable(fornecedores)}
    `;

    $app.querySelector("#btnNovo").addEventListener("click", () => abrirModal($app));
    $app.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const f = fornecedores.find((x) => x.id === Number(btn.dataset.edit));
        abrirModal($app, f);
      });
    });
    $app.querySelectorAll("[data-toggle]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const f = fornecedores.find((x) => x.id === Number(btn.dataset.toggle));
        await Api.alternarAtivoFornecedor(f.id, !f.ativo);
        render($app);
      });
    });
  }

  function listTable(fornecedores) {
    return `
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Nome</th><th>WhatsApp</th><th>E-mail</th><th>Status</th><th></th></tr></thead>
          <tbody>
            ${fornecedores.map((f) => `
              <tr>
                <td>${UI.escapeHtml(f.nome)}</td>
                <td style="font-family:var(--font-mono);font-size:12.5px;">${UI.escapeHtml(f.whatsapp || "—")}</td>
                <td style="font-size:12.5px;">${UI.escapeHtml(f.email || "—")}</td>
                <td><span class="badge ${f.ativo ? "badge--fechada" : "badge--cancelada"}">${f.ativo ? "Ativo" : "Inativo"}</span></td>
                <td style="display:flex;gap:6px;justify-content:flex-end;">
                  <button class="btn btn--sm" data-edit="${f.id}">Editar</button>
                  <button class="btn btn--sm btn--ghost" data-toggle="${f.id}">${f.ativo ? "Desativar" : "Ativar"}</button>
                </td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  }

  function abrirModal($app, fornecedor) {
    const isEdit = !!fornecedor;
    UI.openModal(
      `<div class="modal-head"><h3>${isEdit ? "Editar" : "Novo"} fornecedor</h3><button class="icon-btn" data-close>×</button></div>
       <div style="display:flex;flex-direction:column;gap:14px;">
         <div class="field"><label>Nome *</label><input id="mNome" value="${UI.escapeHtml(fornecedor?.nome || "")}"></div>
         <div class="field"><label>WhatsApp</label><input id="mWhats" placeholder="55DDNÚMERO (só dígitos)" value="${UI.escapeHtml(fornecedor?.whatsapp || "")}"></div>
         <div class="field"><label>E-mail</label><input id="mEmail" value="${UI.escapeHtml(fornecedor?.email || "")}"></div>
         <div class="field"><label>Observações</label><textarea id="mObs">${UI.escapeHtml(fornecedor?.observacoes || "")}</textarea></div>
       </div>
       <div class="modal-actions">
         <button class="btn" data-close>Cancelar</button>
         <button class="btn btn--accent" id="btnSalvar">Salvar</button>
       </div>`,
      {
        onMount(modal) {
          modal.querySelectorAll("[data-close]").forEach((b) => (b.onclick = UI.closeModal));
          modal.querySelector("#btnSalvar").onclick = async () => {
            const nome = modal.querySelector("#mNome").value.trim();
            if (!nome) {
              UI.toast("Informe o nome do fornecedor", "error");
              return;
            }
            const payload = {
              nome,
              whatsapp: modal.querySelector("#mWhats").value.trim() || null,
              email: modal.querySelector("#mEmail").value.trim() || null,
              observacoes: modal.querySelector("#mObs").value.trim() || null,
            };
            try {
              if (isEdit) await Api.atualizarFornecedor(fornecedor.id, payload);
              else await Api.criarFornecedor(payload);
              UI.closeModal();
              UI.toast("Fornecedor salvo", "success");
              render($app);
            } catch (e) {
              UI.toast("Erro: " + e.message, "error");
            }
          };
        },
      }
    );
  }

  return { render };
})();
