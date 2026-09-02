// perm.ts — controle de acesso por perfil (RBAC) no frontend.
//
// As permissões efetivas do usuário chegam do backend (`/api/usuarios/atual`
// e login) como lista achatada `"recurso.acao"` (ex.: "produtos.visualizar").
// O perfil Administrador (superuser) recebe todas as combinações possíveis —
// este helper apenas responde True para tudo.

import { usuarioCorrente } from "./pages/login";

export type AcaoPermissao =
  | "visualizar"
  | "cadastrar"
  | "editar"
  | "excluir"
  | "imprimir"
  | "aprovar"
  | "configurar"
  | "emitir"
  | "exportar"
  | "financeiro"
  | "dados_pessoais"
  | "agendar";

export const ACOES_PERMISSAO: AcaoPermissao[] = [
  "visualizar",
  "cadastrar",
  "editar",
  "excluir",
  "imprimir",
  "aprovar",
  "configurar",
  "emitir",
  "exportar",
  "financeiro",
  "dados_pessoais",
  "agendar",
];

export const ROTULO_ACAO: Record<AcaoPermissao, string> = {
  visualizar: "Visualizar",
  cadastrar: "Cadastrar",
  editar: "Editar",
  excluir: "Excluir",
  imprimir: "Imprimir",
  aprovar: "Aprovar",
  configurar: "Configurar",
  emitir: "Emitir",
  exportar: "Exportar",
  financeiro: "Financeiro",
  dados_pessoais: "Dados pessoais",
  agendar: "Agendar",
};

export function permissoesAtuais(): Set<string> {
  const u = usuarioCorrente();
  return new Set(u?.permissoes ?? []);
}

export function temPermissao(recurso: string, acao: string): boolean {
  const set = permissoesAtuais();
  if (set.size === 0) return false;
  return set.has(`${recurso}.${acao}`);
}

export function podeVisualizar(recurso: string): boolean {
  return temPermissao(recurso, "visualizar");
}
