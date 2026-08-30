// pages/caixa/helpers.ts — utilidades numéricas do caixa.
export function parseNum(v: string): number {
  const n = parseFloat(String(v || "").replace(",", "."));
  return isNaN(n) ? 0 : n;
}

export function fmtNum2(n: number): string {
  return n.toFixed(2).replace(".", ",");
}