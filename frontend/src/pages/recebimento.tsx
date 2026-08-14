// pages/recebimento.tsx — modal compartilhado de recebimento (PDV / balcão).

import { useState } from "react";
import { api } from "../api/client";
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Button, Field, Input, Modal, Select } from "../ui/ui";

export const FORMAS_PAGAMENTO: { valor: string; label: string }[] = [
  { valor: "dinheiro", label: "Dinheiro" },
  { valor: "pix", label: "PIX" },
  { valor: "cheque", label: "Cheque" },
  { valor: "cartao_debito", label: "Cartão débito" },
  { valor: "cartao_credito", label: "Cartão crédito" },
  { valor: "convenio", label: "Convênio" },
  { valor: "boleto", label: "Boleto" },
];

function parseNum(v: string): number {
  const n = parseFloat(String(v || "").replace(",", "."));
  return isNaN(n) ? 0 : n;
}

function fmtNum2(n: number): string {
  return n.toFixed(2).replace(".", ",");
}

export function ModalRecebimento({
  dados,
  onClose,
  onRecebido,
  imprimir = false,
}: {
  dados: { id: number; numero: string; total: number };
  onClose: () => void;
  onRecebido: () => void;
  imprimir?: boolean;
}) {
  const [forma, setForma] = useState("dinheiro");
  const [valor, setValor] = useState(fmtNum2(dados.total));
  const [enviando, setEnviando] = useState(false);

  const valorNum = parseNum(valor);
  const troco = forma === "dinheiro" ? Math.max(0, valorNum - dados.total) : 0;
  const falta = Math.max(0, dados.total - valorNum);

  const confirmar = async () => {
    if (valorNum <= 0) {
      toast("Informe o valor recebido", "error");
      return;
    }
    setEnviando(true);
    try {
      const res = await api.receberOrcamento(dados.id, { forma_pagamento: forma, valor_recebido: valorNum });
      toast(res.troco > 0 ? `Recebido · troco ${fmtMoney(res.troco)}` : "Recebimento registrado", "success");
      onRecebido();
      if (imprimir) void api.imprimirOrcamento(dados.id).catch(() => toast("Venda recebida, mas a impressão falhou", "error"));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={`Recebimento — ${dados.numero}`}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void confirmar()} disabled={enviando}>
            {enviando ? "Registrando…" : "Confirmar recebimento"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="rounded-lg bg-orange-50 p-4 text-center">
          <div className="text-sm text-orange-700">Total a receber</div>
          <div className="text-3xl font-bold text-orange-600">{fmtMoney(dados.total)}</div>
        </div>
        <Field label="Forma de pagamento">
          <Select value={forma} onChange={(e) => setForma(e.target.value)}>
            {FORMAS_PAGAMENTO.map((f) => (
              <option key={f.valor} value={f.valor}>
                {f.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Valor recebido">
          <Input inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} onFocus={(e) => e.target.select()} autoFocus />
        </Field>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => setValor(fmtNum2(dados.total))}>
            Valor exato
          </Button>
          {[50, 100, 200].map((v) => (
            <Button key={v} size="sm" onClick={() => setValor(fmtNum2(Math.ceil(dados.total / v) * v))}>
              Próx. {fmtMoney(v)}
            </Button>
          ))}
        </div>
        {forma === "dinheiro" && troco > 0 && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-emerald-700">
            Troco: <strong>{fmtMoney(troco)}</strong>
          </div>
        )}
        {falta > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-700">
            Falta receber: <strong>{fmtMoney(falta)}</strong>
          </div>
        )}
      </div>
    </Modal>
  );
}
