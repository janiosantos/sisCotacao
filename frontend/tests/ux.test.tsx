// UX-001/002/007: navegação por grupos, tabela com ordenação e acessibilidade.
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Table, TBody, THead, Cell } from "../src/ui/ui";

describe("THead com ordenação (UX-002/007)", () => {
  it("renderiza botão de ordenação com aria-label e aria-sort", () => {
    const html = renderToStaticMarkup(
      <Table>
        <THead cols={["Produto", "Qtd"]} onSort={() => {}} sortState={{ index: 1, dir: "asc" }} />
        <TBody>
          <tr><Cell>P</Cell><Cell>10</Cell></tr>
        </TBody>
      </Table>
    );
    expect(html).toContain('aria-label="ordenar por Produto"');
    expect(html).toContain('aria-sort="ascending"');
    expect(html).toContain("▲");
  });

  it("cabeçalhos sem ordenação não ganham botão", () => {
    const html = renderToStaticMarkup(
      <Table>
        <THead cols={["Estático"]} />
        <TBody><tr><Cell>X</Cell></tr></TBody>
      </Table>
    );
    expect(html).not.toContain("ordenar por");
  });
});

describe("Estados de tabela (UX-005)", () => {
  it("célula com data-label explícito é preservada (mobile card)", () => {
    const html = renderToStaticMarkup(
      <Table>
        <THead cols={["A"]} />
        <TBody>
          <tr><Cell data-label="mantido">vazio</Cell></tr>
        </TBody>
      </Table>
    );
    expect(html).toContain('data-label="mantido"');
  });
});