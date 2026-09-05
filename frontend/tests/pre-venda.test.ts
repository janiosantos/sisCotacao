import { describe, expect, it } from "vitest";
import { deveConsultarCredito, parseBusca, produtoDaBuscaRapida, resolverBuscaAoEnter } from "../src/pages/pre-venda";

describe("parseBusca do PDV", () => {
  it("separa quantidade e produto", () => {
    expect(parseBusca("3*Cabo flexível")).toEqual({ qtd: 3, termo: "Cabo flexível" });
  });

  it("aceita quantidade decimal com vírgula", () => {
    expect(parseBusca("2,5 * tubo")).toEqual({ qtd: 2.5, termo: "tubo" });
  });

  it("mantém uma busca comum com quantidade unitária", () => {
    expect(parseBusca("disjuntor 20A")).toEqual({ qtd: 1, termo: "disjuntor 20A" });
  });

  it("não permite quantidade zero", () => {
    expect(parseBusca("0*cabo")).toEqual({ qtd: 1, termo: "cabo" });
  });
});

describe("exibição de crédito no PDV", () => {
  const vista = { id: 1, nome: "À vista", parcelas: [{ dias: 0, percentual: 100 }] };
  const prazo = { id: 2, nome: "30/60", parcelas: [{ dias: 30, percentual: 50 }, { dias: 60, percentual: 50 }] };

  it("não consulta crédito sem total ou em venda à vista", () => {
    expect(deveConsultarCredito(22, 0, prazo)).toBe(false);
    expect(deveConsultarCredito(22, 100, vista)).toBe(false);
  });

  it("consulta somente cliente identificado em venda a prazo", () => {
    expect(deveConsultarCredito(1, 100, prazo)).toBe(false);
    expect(deveConsultarCredito(22, 100, prazo)).toBe(true);
  });
});

describe("busca por código do PDV", () => {
  const produto = {
    id: 9965,
    sku: "240727-0",
    ean: "7891009866178",
    nome: "Disco de desbaste",
    marca: "Dremel",
    descricao: "Disco 7/8 polegadas",
    ncm: "68042211",
    imagem_url: "/images/disco.jpg",
    preco: 420.82,
    preco_promocional: 399.9,
    unidade_venda: "UN",
    fator_conversao: 1,
    tem_promocao: true,
    rank: 1,
    disponivel: 2,
  };

  it("converte o contrato da busca rápida para o produto do PDV", () => {
    expect(produtoDaBuscaRapida(produto)).toMatchObject({
      id: 9965,
      name: "Disco de desbaste",
      brand: "Dremel",
      price: 399.9,
      ncm: "68042211",
    });
  });

  it("seleciona automaticamente um único código exato", () => {
    const resultado = resolverBuscaAoEnter([
      produto,
      { ...produto, id: 20, nome: "Resultado textual", rank: 3 },
    ]);
    expect(resultado.produto?.id).toBe(9965);
    expect(resultado.sugestoes).toEqual([]);
    expect(resultado.codigoExato).toBe(true);
  });

  it("não escolhe silenciosamente quando o código é ambíguo", () => {
    const resultado = resolverBuscaAoEnter([
      produto,
      { ...produto, id: 20, nome: "Outro produto", rank: 1 },
    ]);
    expect(resultado.produto).toBeUndefined();
    expect(resultado.sugestoes.map((item) => item.id)).toEqual([9965, 20]);
    expect(resultado.codigoExato).toBe(false);
  });
});
