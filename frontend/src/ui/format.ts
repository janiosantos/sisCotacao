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