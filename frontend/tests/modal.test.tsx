import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";
import { Modal } from "../src/ui/ui";

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
});
