// pages/caixa/modal-movimento-caixa.tsx — sangria / reforço (suprimento) do caixa.
import { useState } from "react";
import { api } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";
import { parseNum } from "./helpers";

export function ModalMovimentoCaixa({
  tipo,
  onClose,
  onSalvo,
}: {
  tipo: "sangria" | "suprimento";
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [valor, setValor] = useState("");
  const [descricao, setDescricao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const titulo = tipo === "sangria" ? "Sangria (retirada do caixa)" : "Reforço (suprimento de caixa)";

  const confirmar = async () => {
    const v = parseNum(valor);
    if (v <= 0) {
      toast("Informe um valor maior que zero", "error");
      return;
    }
    setEnviando(true);
    try {
      const res = await api.movimentarCaixa({
        tipo,
        descricao: descricao.trim() || (tipo === "sangria" ? "Sangria" : "Reforço"),
        valor: v,
        forma_pagamento: "dinheiro",
      });
      toast(`${titulo} registrada · novo saldo ${fmtMoney(res.saldo_posterior)}`, "success");
      onSalvo();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={titulo}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void confirmar()} disabled={enviando}>
            {enviando ? "Registrando…" : "Confirmar"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Valor">
          <Input
            inputMode="decimal"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void confirmar();
            }}
            autoFocus
          />
        </Field>
        <Field label="Descrição (opcional)">
          <Input value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder={tipo === "sangria" ? "ex.: depósito no banco" : "ex.: troco inicial"} />
        </Field>
      </div>
    </Modal>
  );
}