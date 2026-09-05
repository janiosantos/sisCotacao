import type { BuscaRapidaItem, ProdutoResumo } from "../api/client";

export function produtoDaBuscaRapida(item: BuscaRapidaItem): ProdutoResumo {
  const promocional = Number(item.preco_promocional || 0);
  const preco = promocional > 0 && promocional < Number(item.preco || 0)
    ? promocional
    : Number(item.preco || 0);
  return {
    id: item.id,
    sku: item.sku || "",
    name: item.nome || "",
    spec: item.descricao || "",
    brand: item.marca || "",
    price: preco,
    imagem_url: item.imagem_url || undefined,
    unidade_venda: item.unidade_venda || "",
    ncm: item.ncm || "",
    category: item.categoria || "",
    subcategory: item.subcategoria || "",
  };
}

export function resolverBuscaAoEnter(itens: BuscaRapidaItem[]): {
  produto?: ProdutoResumo;
  sugestoes: ProdutoResumo[];
  codigoExato: boolean;
} {
  const exatos = itens.filter((item) => item.rank <= 1);
  const selecionaveis = (exatos.length ? exatos : itens).map(produtoDaBuscaRapida);
  if (selecionaveis.length === 1) {
    return { produto: selecionaveis[0], sugestoes: [], codigoExato: exatos.length === 1 };
  }
  return { sugestoes: selecionaveis, codigoExato: false };
}

export function rotuloProduto(produto: ProdutoResumo): string {
  return [produto.sku, produto.name].filter(Boolean).join(" - ");
}
