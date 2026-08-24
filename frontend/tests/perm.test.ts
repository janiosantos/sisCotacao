// tests/perm.test.ts — controle de acesso por perfil (RBAC) no frontend.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { temPermissao, ACOES_PERMISSAO } from "../src/perm";
import * as login from "../src/pages/login";

function mockUsuario(permissoes: string[]) {
  vi.mocked(login.usuarioCorrente).mockReturnValue({
    id: 1,
    nome: "Teste",
    login: "teste",
    perfil: "vendedor",
    ativo: true,
    criado_em: "",
    autenticado: true,
    permissoes,
  } as never);
}

vi.mock("../src/pages/login", () => ({
  usuarioCorrente: vi.fn(() => null),
}));

beforeEach(() => {
  vi.mocked(login.usuarioCorrente).mockReset();
  vi.mocked(login.usuarioCorrente).mockReturnValue(null as never);
});

describe("temPermissao", () => {
  it("retorna true quando o usuário tem a ação no recurso", () => {
    mockUsuario(["produtos.visualizar", "produtos.cadastrar"]);
    expect(temPermissao("produtos", "visualizar")).toBe(true);
    expect(temPermissao("produtos", "cadastrar")).toBe(true);
  });

  it("retorna false quando não tem a ação", () => {
    mockUsuario(["produtos.visualizar"]);
    expect(temPermissao("produtos", "excluir")).toBe(false);
  });

  it("retorna false sem usuário/sessão", () => {
    expect(temPermissao("produtos", "visualizar")).toBe(false);
  });

  it("administrador (todas as combinações) acessa tudo", () => {
    const todas = ACOES_PERMISSAO.flatMap((a) =>
      ["produtos", "usuarios", "estoque"].map((r) => `${r}.${a}`),
    );
    mockUsuario(todas);
    expect(temPermissao("usuarios", "excluir")).toBe(true);
    expect(temPermissao("estoque", "configurar")).toBe(true);
  });

  it("negação por usuário remove a ação da lista efetiva", () => {
    // O backend já devolve a lista efetiva (perfis+conceder−negar); o frontend
    // apenas reflete. Ação negada não aparece => temPermissao false.
    mockUsuario(["pre-venda.visualizar", "pre-venda.editar"]);
    expect(temPermissao("pre-venda", "visualizar")).toBe(true);
    expect(temPermissao("pre-venda", "cadastrar")).toBe(false);
  });
});