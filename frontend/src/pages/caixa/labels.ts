// pages/caixa/labels.ts — status e formas de pagamento do caixa (ECF).
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

// Ordem/atalhos das formas de pagamento no caixa (ECF).
export const FORMAS_CAIXA: { valor: string; label: string; tecla: string }[] = [
  { valor: "dinheiro", label: "Dinheiro", tecla: "F1" },
  { valor: "pix", label: "PIX", tecla: "F2" },
  { valor: "cartao_credito", label: "Cartão crédito", tecla: "F3" },
  { valor: "cartao_debito", label: "Cartão débito", tecla: "F4" },
  { valor: "cheque", label: "Cheque", tecla: "F5" },
  { valor: "convenio", label: "Convênio", tecla: "F6" },
  { valor: "boleto", label: "Boleto", tecla: "F7" },
];