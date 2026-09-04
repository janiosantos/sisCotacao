import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, limparCacheApi, mensagemErro } from "../src/api/client";

// Contrato de erro da API (P6): toda falha lança ApiError com status/code.

const fetchMock = vi.fn();
globalThis.fetch = fetchMock as unknown as typeof fetch;

function res(status: number, body: unknown, extra?: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...(extra || {}) },
  });
}

beforeEach(() => {
  fetchMock.mockReset();
  limparCacheApi();
});

describe("request", () => {
  it("retorna JSON em 200", async () => {
    fetchMock.mockResolvedValue(res(200, [{ id: 1 }]));
    const r = await api.listarPagar({});
    expect(Array.isArray(r)).toBe(true);
    expect(r).toHaveLength(1);
  });

  it("reutiliza GET no cache curto e invalida após mutação", async () => {
    fetchMock
      .mockResolvedValueOnce(res(200, [{ id: 1 }]))
      .mockResolvedValueOnce(res(200, { id: 2 }))
      .mockResolvedValueOnce(res(200, [{ id: 1 }, { id: 2 }]));

    await api.listarPagar({});
    await api.listarPagar({});
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await api.criarCliente({ nome: "Cliente cache" });
    await api.listarPagar({});
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("lança ApiError com status/code/details em 4xx", async () => {
    fetchMock.mockResolvedValue(res(400, { error: "Limite excedido", code: "sem_credito" }));
    try {
      await api.listarPagar({});
      expect.unreachable("deveria lançar");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(400);
      expect(err.code).toBe("sem_credito");
      expect(err.message).toBe("Limite excedido");
      expect(err.details?.error).toBe("Limite excedido");
    }
  });

  it("rejeita resposta de lista sem o contrato mínimo", async () => {
    fetchMock.mockResolvedValue(res(200, { items: [] }));
    await expect(api.listarProdutosCadastro()).rejects.toMatchObject({
      status: 502,
      code: "contrato_invalido",
    });
  });

  it("lança ApiError com status em 5xx", async () => {
    fetchMock.mockResolvedValue(res(502, { error: "Backend indisponível" }));
    try {
      await api.listarPagar({});
      expect.unreachable();
    } catch (e) {
      const err = e as ApiError;
      expect(err.status).toBe(502);
      expect(err.message).toBe("Backend indisponível");
    }
  });

  it("lança 'Servidor indisponível' em falha de rede", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api.listarPagar({})).rejects.toThrow("Servidor indisponível");
  });

  it("usa contratos tipados para sessão e importação da galeria", async () => {
    fetchMock
      .mockResolvedValueOnce(res(200, { available: true, url: "/galeria/?session=x", max_selection: 12 }))
      .mockResolvedValueOnce(res(201, { imagens: ["/images/foto.jpg"], total: 1, deduplicadas: 0 }));

    const status = await api.statusGaleriaProdutos();
    expect(status.available).toBe(true);
    await api.importarImagensGaleria(42, [7]);

    expect(fetchMock.mock.calls[0][0]).toBe("/api/produtos/imagens/galeria/status");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/produtos-cadastro/42/imagens/galeria");
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ image_ids: [7] });
  });
});

describe("mensagemErro", () => {
  it("formata ApiError pela message", () => {
    expect(mensagemErro(new ApiError(403, "Permissão negada", "sem_permissao"))).toBe("Permissão negada");
  });
  it("fallback para status quando sem message", () => {
    expect(mensagemErro(new ApiError(500, ""))).toBe("Erro 500");
  });
  it("propaga Error e valores primitivos", () => {
    expect(mensagemErro(new Error("boom"))).toBe("boom");
    expect(mensagemErro("texto")).toBe("texto");
  });
});
