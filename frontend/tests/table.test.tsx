// tests/table.test.tsx — tabela responsiva (v2.20.1): cada linha vira card
// no mobile com rótulo do cabeçalho (data-label) e colunas no desktop (lg).

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Cell, Table, TBody, THead } from "../src/ui/ui";

describe("Table (responsiva mobile)", () => {
  it("injeta data-label por coluna em cada célula", () => {
    const html = renderToStaticMarkup(
      <Table>
        <THead cols={["Nome", "Valor"]} />
        <TBody>
          <tr>
            <Cell>Parafuso</Cell>
            <Cell>R$ 2,00</Cell>
          </tr>
          <tr>
            <Cell>Prego</Cell>
            <Cell>R$ 1,00</Cell>
          </tr>
        </TBody>
      </Table>
    );
    expect(html.match(/data-label/g)).toHaveLength(4);
    expect(html).toContain('data-label="Nome"');
    expect(html).toContain('data-label="Valor"');
  });

  it("preserva data-label explícito (EmptyRow)", () => {
    const html = renderToStaticMarkup(
      <Table>
        <THead cols={["Nome", "Valor"]} />
        <TBody>
          <tr>
            <td data-label="" colSpan={2}>
              Vazio
            </td>
          </tr>
        </TBody>
      </Table>
    );
    expect(html).toContain('data-label=""');
  });

  it("aplica classes de card no mobile e coluna no desktop", () => {
    const html = renderToStaticMarkup(
      <Table>
        <THead cols={["Nome"]} />
        <TBody>
          <tr>
            <Cell>A</Cell>
          </tr>
        </TBody>
      </Table>
    );
    expect(html).toContain("mob-card");
    expect(html).toContain("lg:table-header-group");
    expect(html).toContain("lg:table-cell");
  });
});