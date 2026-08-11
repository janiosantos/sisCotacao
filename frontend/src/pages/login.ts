// pages/login.ts — tela de login e gate de autenticação do app.

import { api, type UsuarioAtual } from "../api/client";
import { closeModal, openModal, toast } from "../ui/dom";

let atual: UsuarioAtual | null = null;

export function usuarioCorrente(): UsuarioAtual | null {
  return atual;
}

export function estaAutenticado(): boolean {
  return !!atual?.autenticado;
}

export async function carregarSessao(): Promise<boolean> {
  try {
    atual = await api.usuarioAtual();
    return !!atual?.autenticado;
  } catch {
    atual = null;
    return false;
  }
}

export async function entrar(login: string, senha: string): Promise<boolean> {
  try {
    atual = await api.login(login, senha);
    return true;
  } catch (e) {
    toast("Falha no login: " + (e as Error).message, "error");
    return false;
  }
}

export async function sair(): Promise<void> {
  try { await api.logout(); } catch { /* off-line */ }
  atual = null;
}

export function renderLogin($app: HTMLElement): void {
  $app.innerHTML = `
    <div class="login-screen" style="display:flex;align-items:center;justify-content:center;min-height:100%;">
      <div class="login-box" style="max-width:340px;width:100%;border:1px solid var(--line);border-radius:12px;padding:24px;background:var(--bg-card);">
        <h1 class="page-title" style="margin-bottom:4px;">Entrar</h1>
        <p class="page-sub">Acesse o sistema com seu usuário.</p>
        <div style="display:flex;flex-direction:column;gap:14px;margin-top:16px;">
          <div class="field"><label>Login</label><input id="lgLogin" autocomplete="username"></div>
          <div class="field"><label>Senha</label><input id="lgSenha" type="password" autocomplete="current-password"></div>
          <button class="btn btn--accent" id="lgEntrar">Entrar</button>
        </div>
      </div>
    </div>
  `;

  const $login = $app.querySelector<HTMLInputElement>("#lgLogin");
  const $senha = $app.querySelector<HTMLInputElement>("#lgSenha");
  const $entrar = $app.querySelector<HTMLButtonElement>("#lgEntrar");
  const tentar = async () => {
    const ok = await entrar($login!.value.trim(), $senha!.value);
    if (ok) {
      toast("Bem-vindo!", "success");
      location.reload();
    }
  };
  $entrar!.addEventListener("click", () => void tentar());
  $senha!.addEventListener("keydown", (e) => { if (e.key === "Enter") void tentar(); });
  $login!.focus();
}

export function abrirModalPrimeiroAcesso(): void {
  openModal(`
    <div class="modal-head"><h3>Bem-vindo — primeiro acesso</h3><button class="icon-btn" data-close>×</button></div>
    <p style="font-size:13px;color:var(--ink-soft);">Ainda não há usuários cadastrados no sistema. Crie o primeiro usuário administrador para começar.</p>
    <div style="display:flex;flex-direction:column;gap:12px;margin-top:12px;">
      <div class="field"><label>Nome</label><input id="puNome"></div>
      <div class="field"><label>Login</label><input id="puLogin"></div>
      <div class="field"><label>Senha (mín. 4)</label><input id="puSenha" type="password"></div>
    </div>
    <div class="modal-actions">
      <button class="btn" data-close>Cancelar</button>
      <button class="btn btn--accent" id="puCriar">Criar administrador</button>
    </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLButtonElement>("#puCriar")!.onclick = async () => {
          const nome = modal.querySelector<HTMLInputElement>("#puNome")!.value.trim();
          const login = modal.querySelector<HTMLInputElement>("#puLogin")!.value.trim();
          const senha = modal.querySelector<HTMLInputElement>("#puSenha")!.value;
          if (!nome || !login || senha.length < 4) {
            toast("Preencha nome, login e senha (mín. 4)", "error");
            return;
          }
          try {
            await api.criarUsuario({ nome, login, senha, perfil: "admin" });
            closeModal();
            const ok = await entrar(login, senha);
            if (ok) {
              toast("Administrador criado. Bem-vindo!", "success");
              location.reload();
            }
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}