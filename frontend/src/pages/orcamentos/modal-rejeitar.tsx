// pages/orcamentos/modal-rejeitar.tsx — rejeição de desconto com motivo.
import { useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalRejeitar({ id, onClose, onOk }: { id: number; onClose: () => void; onOk: () => void }) {
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);

  const tentar = async () => {
    if (!motivo.trim()) {
      toast("Informe o motivo da rejeição", "error");
      return;
    }
    setEnviando(true);
    try {
      await api.rejeitarDescontoOrcamento(id, motivo.trim());
      toast("Desconto rejeitado", "success");
      onOk();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Rejeitar desconto"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="danger" onClick={() => void tentar()} disabled={enviando}>
            {enviando ? "Rejeitando…" : "Rejeitar"}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">Informe o motivo da rejeição do desconto.</p>
      <Field label="Motivo *">
        <Input value={motivo} onChange={(e) => setMotivo(e.target.value)} autoFocus />
      </Field>
    </Modal>
  );
}