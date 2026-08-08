// client.ts — cliente HTTP tipado para a API do catalog_server.

export interface ProdutoResumo {
  id: number;
  sku: string;
  name: string;
  im_url?: string;
  brand?: string;
}

export interface HistoricoPreco {
  fornecedor_id: number;
  fornecedor_nome: string;
  cotacao_id: number;
  cotacao_numero: number;
  preco_unitario: number;
  prazo_entrega_dias: number | null;
  registrado_em: string;
  validade_preco_em: string | null;
}

export interface ProdutoComHistorico {
  id: number;
  sku: string;
  name: string;
}

export type Metodo = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function request<T>(method: Metodo, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = { method, headers: {} };
  if (body !== undefined) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.error || detail;
    } catch {
      /* resposta não-JSON */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function qs(params: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  return parts.length ? "?" + parts.join("&") : "";
}

export const api = {
  listarProdutos: (params: Record<string, unknown> = {}) =>
    request<ProdutoResumo[]>("GET", "/api/produtos" + qs(params)),

  historicoPrecos: (produtoId: number) =>
    request<HistoricoPreco[]>("GET", "/api/historico-precos" + qs({ produto_id: produtoId })),

  produtosComHistorico: () =>
    request<ProdutoComHistorico[]>("GET", "/api/historico-precos/produtos"),
};