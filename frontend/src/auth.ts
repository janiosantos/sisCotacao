// auth.ts — lógica de primeiro acesso e manutenção de sessão.

import { api } from "./api/client";
import { abrirModalPrimeiroAcesso } from "./pages/login";

let rodado = false;

export function startupAuth(): void {
  if (rodado) return;
  rodado = true;
  void api
    .usuariosVazio()
    .then((res) => {
      if (res.vazio) abrirModalPrimeiroAcesso();
    })
    .catch(() => {});
}