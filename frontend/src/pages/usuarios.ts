// pages/usuarios.ts — gestão de usuários e login.

import { api, type Usuario, type UsuarioPayload } from "../api/client";
import { escapeHtml } from "../ui/format";
import { closeModal, openModal, toast } from "../ui/dom";

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando usuários…</div>`;
  let usuarios: Usuario[] = [];
  try {
    usuarios = await api.listarUsuarios();
  } catch (e) {
    toast("Erro ao carregar usuários: " + (e as Error).message, "error");
  }

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Usuários</h1>
        <p class="page-sub">Contas de acesso ao sistema, com perfil de permissão.</p>
      </div>
      <button class="btn btn--accent" id="btnNovo">+ Novo usuário</button>
    </div>
    <div id="tabelaWrap"></div>
  `;

  const $t = $app.querySelector<HTMLElement>("#tabelaWrap")!;
  $t.innerHTML = usuariosTabela(usuarios);

  $app.querySelector<HTMLButtonElement>("#btnNovo")!.addEventListener("click", () => abrirModal($app, null));
  $app.querySelectorAll<HTMLElement>("[data-edit]").forEach((b) => {
    b.addEventListener("click", () => {
      const u = usuarios.find((x) => x.id === Number(b.dataset.edit))!;
      abrirModal($app, u);
    });
  });
  $app.querySelectorAll<HTMLElement>("[data-toggle]").forEach((b) => {
    b.addEventListener("click", async () => {
      const u = usuarios.find((x) => x.id === Number(b.dataset.toggle))!;
      await api.alternarAtivoUsuario(u.id, !u.ativo);
      await render($app);
    });
  });
}

function usuariosTabela(usuarios: Usuario[]): string {
  if (!usuarios.length) {
    return `<div class="empty-box"><p>Nenhum usuário cadastrado</p><p>Crie o primeiro usuário para controlar o acesso ao sistema.</p></div>`;
  }
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>Nome</th><th>Login</th><th>Perfil</th><th>Status</th><th></th></tr></thead>
        <tbody>
          ${usuarios.map((u) => `
            <tr>
              <td>${escapeHtml(u.nome)}</td>
              <td style="font-family:var(--font-mono);font-size:12.5px;">${escapeHtml(u.login)}</td>
              <td><span class="badge">${escapeHtml(u.perfil)}</span></td>
              <td><span class="badge ${u.ativo ? "badge--fechada" : "badge--cancelada"}">${u.ativo ? "Ativo" : "Inativo"}</span></td>
              <td style="display:flex;gap:6px;justify-content:flex-end;">
                <button class="btn btn--sm" data-edit="${u.id}">Editar</button>
                <button class="btn btn--sm btn--ghost" data-toggle="${u.id}">${u.ativo ? "Desativar" : "Ativar"}</button>
              </td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function abrirModal($app: HTMLElement, usuario: Usuario | null): void {
  const isEdit = !!usuario;
  openModal(
    `<div class="modal-head"><h3>${isEdit ? "Editar" : "Novo"} usuário</h3><button class="icon-btn" data-close>×</button></div>
     <div style="display:flex;flex-direction:column;gap:14px;">
       <div class="field"><label>Nome *</label><input id="mNome" value="${escapeHtml(usuario?.nome || "")}"></div>
       <div class="field"><label>Login *</label><input id="mLogin" autocomplete="off" value="${escapeHtml(usuario?.login || "")}" ${isEdit ? "disabled" : ""}></div>
       <div class="field"><label>Senha ${isEdit ? "(deixe em branco para manter)" : "*"}</label><input id="mSenha" type="password" autocomplete="new-password"></div>
       <div class="field"><label>Perfil</label>
         <select id="mPerfil">
           <option value="vendedor" ${usuario?.perfil === "vendedor" ? "selected" : ""}>Vendedor</option>
           <option value="admin" ${usuario?.perfil === "admin" ? "selected" : ""}>Admin</option>
         </select>
       </div>
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
          const senha = modal.querySelector<HTMLInputElement>("#mSenha")!.value;
          if (!nome) { toast("Informe o nome do usuário", "error"); return; }
          if (!isEdit && senha.length < 4) { toast("Informe uma senha com pelo menos 4 caracteres", "error"); return; }
          const payload: UsuarioPayload = {
            nome,
            login: usuario ? usuario.login : modal.querySelector<HTMLInputElement>("#mLogin")!.value.trim(),
            senha: senha.length ? senha : undefined,
            perfil: modal.querySelector<HTMLSelectElement>("#mPerfil")!.value,
          };
          try {
            if (isEdit && usuario) await api.atualizarUsuario(usuario.id, payload);
            else await api.criarUsuario(payload);
            closeModal();
            toast("Usuário salvo", "success");
            await render($app);
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}