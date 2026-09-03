import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";
import { type OrcamentoDetalhe } from "../src/api/client";
import { Modal } from "../src/ui/ui";
import { ModalDetalhe } from "../src/pages/orcamentos/modal-detalhe";

describe("Modal", () => {
  let root: Root | null = null;
  let container: HTMLDivElement | null = null;

  afterEach(() => {
    if (root) act(() => root?.unmount());
    container?.remove();
    root = null;
    container = null;
  });

  it("preserva o foco no campo após uma nova renderização do formulário", () => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    act(() => {
      root?.render(
        <Modal open onClose={() => undefined} title="Autorizar">
          <input aria-label="Login" value="" readOnly />
        </Modal>,
      );
    });

    const campo = container.querySelector<HTMLInputElement>("input");
    expect(campo).not.toBeNull();
    campo?.focus();

    act(() => {
      root?.render(
        <Modal open onClose={() => undefined} title="Autorizar">
          <input aria-label="Login" value="g" readOnly />
        </Modal>,
      );
    });

    expect(document.activeElement).toBe(container.querySelector("input"));
  });

  it("não oferece recebimento dentro do detalhe de Orçamentos", () => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    const detalhe = {
      id: 43,
      numero: "ORC0043",
      cliente: "Cliente de teste",
      contato: "",
      status: "finalizado",
      desconto: 0,
      subtotal: 100,
      total: 100,
      validade_dias: 7,
      criado_em: "2026-09-03T10:00:00",
      observacoes: "",
      n_itens: 1,
      n_parcelas: 2,
      itens: [{ nome: "Produto de teste", quantidade: 1, preco_unitario: 100 }],
    } as OrcamentoDetalhe;

    act(() => {
      root?.render(
        <ModalDetalhe
          d={detalhe}
          onClose={() => undefined}
          onAutorizar={() => undefined}
          onRejeitar={() => undefined}
          onReabrir={() => undefined}
          onExcluir={() => undefined}
        />,
      );
    });

    expect(container.textContent).not.toContain("Receber");
    expect(container.textContent).toContain("Contas a receber");
  });
});
