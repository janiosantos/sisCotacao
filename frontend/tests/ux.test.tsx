// UX-001/002/007: navegação por grupos, tabela com ordenação e acessibilidade.
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { PageHeader, Paginacao, Table, TBody, THead, Cell } from "../src/ui/ui";

describe("PageHeader com contexto (UX-001)", () => {
  it("renderiza o rótulo de contexto acima do título", () => {
    const html = renderToStaticMarkup(<PageHeader title="Clientes" contexto="Comercial · Cadastros" />);
    expect(html).toContain("Comercial · Cadastros");
    expect(html).toContain(">Clientes</h1>");
  });
});

describe("Paginacao (UX-002/006)", () => {
  it("mostra total e navegação com aria-label", () => {
    const html = renderToStaticMarkup(<Paginacao total={120} pagina={1} porPagina={50} onChange={() => {}} />);
    expect(html).toContain("120 registro(s)");
    expect(html).toContain("de 3");
    expect(html).toContain('aria-label="Próxima página"');
  });
});

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