// pages/precos/modal-aplicar-promocao.tsx - módulo Preços (ModalAplicarPromocao).

import { useEffect, useState } from "react";
import { api, type Promocao } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Field, Modal, Textarea } from "../../ui/ui";

export function ModalAplicarPromocao({ promocao, onClose }: { promocao: Promocao | null; onClose: () => void }) {
  const [ids, setIds] = useState("");

  useEffect(() => {
    if (promocao) setIds("");
  }, [promocao]);

  const aplicar = async () => {
    if (!promocao) return;
    const texto = ids.trim();
    if (!texto) {
      toast("Informe ao menos um ID", "error");
      return;
    }
    const lista = texto
      .split(",")
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n > 0);
    if (!lista.length) {
      toast("IDs inválidos", "error");
      return;
    }
    try {
      const res = await api.aplicarPromocao(promocao.id, lista);
      toast(`${res.aplicados} itens aplicados`, "success");
      onClose();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={promocao !== null}
      onClose={onClose}
      title={`Aplicar — ${promocao?.nome ?? ""}`}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void aplicar()}>
            Aplicar
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        Aplica a promoção a produtos por ID do produto. Informe os IDs separados por vírgula.{" "}
        {promocao?.tipo === "percentual"
          ? `Desconto de ${promocao.valor}% sobre o preço base.`
          : `Preço fixo de ${fmtMoney(promocao?.valor ?? 0)}.`}
      </p>
      <Field label="IDs dos produtos (separados por vírgula)">
        <Textarea rows={3} placeholder="Ex.: 1, 2, 3, 10, 15" value={ids} onChange={(e) => setIds(e.target.value)} />
      </Field>
    </Modal>
  );
}


