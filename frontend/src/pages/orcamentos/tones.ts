// pages/orcamentos/tones.ts — labels e tons de status/desconto (compartilhados).
export const STATUS_LABELS: Record<string, string> = {
  rascunho: "Rascunho",
  ativo: "Ativo",
  em_analise: "Em análise",
  liberado: "Liberado",
  finalizado: "Finalizado",
  recebido: "Recebido",
  cancelado: "Cancelado",
  devolvido: "Devolvido",
};

export const DESCONTO_LABELS: Record<string, string> = {
  ok: "Dentro da alçada",
  pendente: "Pendente",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
};

export function statusTone(status: string): "green" | "red" | "amber" | "gray" {
  if (status === "recebido") return "green";
  if (status === "finalizado") return "amber";
  if (status === "cancelado" || status === "devolvido") return "red";
  return "gray";
}

export function descontoTone(s: string | undefined): "green" | "red" | "amber" | "gray" {
  if (s === "aprovado" || s === "ok") return "green";
  if (s === "rejeitado") return "red";
  if (s === "pendente") return "amber";
  return "gray";
}