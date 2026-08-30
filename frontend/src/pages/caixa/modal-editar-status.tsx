// pages/caixa/modal-editar-status.tsx — edição manual de status do pedido no caixa.
import { useState } from "react";
import { api, type OrcamentoLista } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Modal, Select } from "../../ui/ui";
import { STATUS_LABELS } from "./labels";

export function ModalEditarStatus({
  d,
  onClose,
  onSalvo,
}: {
  d: OrcamentoLista;
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [status, setStatus] = useState<string>(d.status);

  const salvar = async () => {
    try {
      await api.atualizarOrcamento(d.id, { status });
      toast("Status atualizado", "success");
      onSalvo();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={`Editar status — ${d.numero}`}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <Field label="Status">
        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
      </Field>
    </Modal>
  );
}