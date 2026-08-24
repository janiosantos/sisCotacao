// tests/format.test.ts — esqueleto da suíte vitest do frontend.
import { describe, expect, it } from "vitest";
import { escapeHtml, fmtMoney, toDate } from "../src/ui/format";

describe("escapeHtml", () => {
  it("escapa caracteres HTML", () => {
    expect(escapeHtml(`<script>alert("x&y")</script>`)).toBe(
      "&lt;script&gt;alert(&quot;x&amp;y&quot;)&lt;/script&gt;",
    );
  });
});

describe("fmtMoney", () => {
  it("formata BRL pt-BR", () => {
    expect(fmtMoney(1500.5)).toBe("R$ 1.500,50");
  });

  it("retorna travessão para valores vazios", () => {
    expect(fmtMoney(null)).toBe("—");
    expect(fmtMoney(undefined)).toBe("—");
  });
});

describe("toDate", () => {
  it("converte formato SQLite UTC", () => {
    const d = toDate("2026-08-23 15:00:00");
    expect(d).not.toBeNull();
    expect(d!.getUTCFullYear()).toBe(2026);
  });

  it("retorna null para valores inválidos", () => {
    expect(toDate(null)).toBeNull();
    expect(toDate("not-a-date")).toBeNull();
  });
});