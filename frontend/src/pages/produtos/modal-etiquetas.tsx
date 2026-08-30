// pages/produtos/modal-etiquetas.tsx — geração de etiquetas de preço.
import { useState } from "react";
import { toast } from "../../ui/dom";
import { Button, Field, Modal, Textarea } from "../../ui/ui";

export function ModalEtiquetas({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [ids, setIds] = useState("");
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Etiquetas de preço"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button
            variant="primary"
            onClick={() => {
              const texto = ids.trim();
              if (!texto) {
                toast("Informe ao menos um ID", "error");
                return;
              }
              const idList = texto.split(",").map((s) => s.trim()).filter(Boolean).join(",");
              window.open(`/etiquetas/imprimir?ids=${idList}`, "_blank");
            }}
          >
            Gerar etiquetas
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-gray-500">Informe os IDs dos produtos (separados por vírgula) para gerar a folha de etiquetas.</p>
      <Field label="IDs dos produtos">
        <Textarea rows={3} placeholder="Ex.: 1, 2, 3, 10" value={ids} onChange={(e) => setIds(e.target.value)} />
      </Field>
    </Modal>
  );
}