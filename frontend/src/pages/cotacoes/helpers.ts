// pages/cotacoes/helpers.ts — labels, tons e cálculos de embalagem (compartilhados).
export const STATUS_LABELS: Record<string, string> = {
  aberta: "Aberta",
  fechada: "Fechada",
  cancelada: "Cancelada",
  pendente: "Pendente",
  analise: "Pronta para Analisar",
  finalizada: "Finalizada",
  respondido: "Respondido",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] || status;
}

export function statusTone(status: string): "green" | "red" | "gray" {
  if (status === "fechada" || status === "finalizada") return "green";
  if (status === "cancelada") return "red";
  return "gray";
}

export function qtdEmbalagens(quantidade: number, fator: number): number {
  return Math.ceil(quantidade / fator);
}