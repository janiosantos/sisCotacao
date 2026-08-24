// format.ts — helpers de formatação (mesmo comportamento de ui.js).

export function escapeHtml(value: unknown): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function fmtMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function toDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  // SQLite grava "YYYY-MM-DD HH:MM:SS" em UTC (datetime('now')).
  const d = new Date(String(iso).replace(" ", "T") + "Z");
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtDate(iso: string | null): string {
  const d = toDate(iso);
  if (!d) return "—";
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function fmtDateTime(iso: string | null): string {
  const d = toDate(iso);
  if (!d) return "—";
  return (
    d.toLocaleDateString("pt-BR") +
    " " +
    d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
  );
}

// ── Máscaras ───────────────────────────────────────────────

/** Remove tudo que não é dígito. */
export function soDigitos(v: unknown): string {
  return String(v ?? "").replace(/\D/g, "");
}

/** Máscara de CPF (000.000.000-00) ou CNPJ (00.000.000/0000-00). */
export function maskDoc(value: string, tipo: "f" | "j" = "f"): string {
  const d = soDigitos(value);
  if (tipo === "j") {
    if (d.length <= 14) {
      return d
        .replace(/^(\d{2})(\d)/, "$1.$2")
        .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
        .replace(/\.(\d{3})(\d)/, ".$1/$2")
        .replace(/(\d{4})(\d)/, "$1-$2");
    }
    return d.slice(0, 14)
      .replace(/^(\d{2})(\d)/, "$1.$2")
      .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/\.(\d{3})(\d)/, ".$1/$2")
      .replace(/(\d{4})(\d)/, "$1-$2");
  }
  return d
    .slice(0, 11)
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/\.(\d{3})(\d)/, ".$1.$2")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

/** Máscara de telefone/whatsapp: (11) 98765-4321. */
export function maskFone(value: string): string {
  const d = soDigitos(value).slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return d.replace(/^(\d{2})(\d)/, "($1) $2");
  if (d.length <= 10) return d.replace(/^(\d{2})(\d{4})(\d)/, "($1) $2-$3");
  return d.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
}

/** Máscara de CEP: 00000-000. */
export function maskCep(value: string): string {
  const d = soDigitos(value).slice(0, 8);
  if (d.length <= 5) return d;
  return d.replace(/^(\d{5})(\d)/, "$1-$2");
}

/** Máscara de IE — apenas dígitos (formato varia por UF). */
export function maskIe(value: string): string {
  return soDigitos(value);
}

/** Valida dígitos verificadores de CPF (null se inválido). */
export function validarCpf(doc: string): boolean {
  const d = soDigitos(doc);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  const calc = (base: number) => {
    let sum = 0;
    for (let i = 0; i < base; i++) sum += parseInt(d[i], 10) * (base + 1 - i);
    const r = (sum * 10) % 11;
    return r === 10 ? 0 : r;
  };
  return calc(9) === parseInt(d[9], 10) && calc(10) === parseInt(d[10], 10);
}

/** Valida dígitos verificadores de CNPJ (null se inválido). */
export function validarCnpj(doc: string): boolean {
  const d = soDigitos(doc);
  if (d.length !== 14 || /^(\d)\1{13}$/.test(d)) return false;
  const pesos = (base: number) => {
    const seq = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    let sum = 0;
    for (let i = 0; i < base; i++) sum += parseInt(d[i], 10) * (seq[base - 1 - i] ?? seq[base + 11 - i]);
    const r = sum % 11;
    return r < 2 ? 0 : 11 - r;
  };
  return pesos(12) === parseInt(d[12], 10) && pesos(13) === parseInt(d[13], 10);
}