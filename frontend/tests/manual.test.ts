import { describe, expect, it } from "vitest";
import { MANUAL_ENTRIES } from "../src/manual-content";
import { capturasDoManual } from "../src/manual-capturas";

describe("manual visual integrado", () => {
  it("mantém uma captura incorporada para cada módulo documentado", () => {
    expect(MANUAL_ENTRIES.length).toBeGreaterThan(0);
    expect(MANUAL_ENTRIES.every((entry) => capturasDoManual(entry.id).length > 0)).toBe(true);
  });

  it("não repete a mesma imagem em módulos diferentes", () => {
    const srcs = MANUAL_ENTRIES.flatMap((entry) => capturasDoManual(entry.id).map((capture) => capture.src));
    expect(new Set(srcs).size).toBe(srcs.length);
  });
});
