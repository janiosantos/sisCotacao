// pages/vendedores/modal-form.tsx — criação/edição de vendedor.
import { useEffect, useState } from "react";
import { api, type Vendedor, type VendedorPayload } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalVendedorForm({
  vendedor,
  onClose,
  onSaved,
}: {
  vendedor: Vendedor | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState("");
  const [comissao, setComissao] = useState("");

  useEffect(() => {
    setNome(vendedor?.nome ?? "");
    setComissao(vendedor ? String(vendedor.comissao_pct) : "");
  }, [vendedor]);

  const salvar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome do vendedor", "error");
      return;
    }
    const payload: VendedorPayload = { nome: nome.trim(), comissao_pct: Number(comissao) || 0 };
    try {
      if (vendedor) await api.atualizarVendedor(vendedor.id, payload);
      else await api.criarVendedor(payload);
      onClose();
      toast("Vendedor salvo", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={vendedor ? "Editar vendedor" : "Novo vendedor"}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Nome *">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
        <Field label="Comissão (%)">
          <Input type="number" min={0} step="0.01" value={comissao} onChange={(e) => setComissao(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}