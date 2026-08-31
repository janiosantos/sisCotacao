import { describe, expect, it } from "vitest";
import { parseBusca } from "../src/pages/pre-venda";

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
