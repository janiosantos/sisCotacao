// tests/format.test.ts — esqueleto da suíte vitest do frontend.
import { describe, expect, it } from "vitest";
import { escapeHtml, fmtMoney, maskDoc, normalizarTipoPessoa, toDate, validarCnpj, validarCpf } from "../src/ui/format";

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

describe("documentos", () => {
  it("valida CNPJ formatado e sem mascara", () => {
    expect(validarCnpj("04.252.011/0001-10")).toBe(true);
    expect(validarCnpj("04252011000110")).toBe(true);
    expect(validarCnpj("04.252.011/0001-11")).toBe(false);
  });

  it("mantem CPF e normaliza tipo juridico ao editar cadastro", () => {
    expect(validarCpf("529.982.247-25")).toBe(true);
    expect(normalizarTipoPessoa("J")).toBe("j");
    expect(maskDoc("04252011000110", normalizarTipoPessoa("J"))).toBe("04.252.011/0001-10");
  });
});
