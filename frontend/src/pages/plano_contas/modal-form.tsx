// pages/plano_contas/modal-form.tsx — criação/edição de conta do plano de contas.
import { useEffect, useState } from "react";
import { api, type ContaPlano, type ContaPlanoPayload } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select } from "../../ui/ui";

export function ModalContaForm({
  conta,
  onClose,
  onSaved,
}: {
  conta: ContaPlano | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({ codigo: "", nome: "", tipo: "receita" as "receita" | "despesa" });

  useEffect(() => {
    setForm({ codigo: conta?.codigo ?? "", nome: conta?.nome ?? "", tipo: (conta?.tipo ?? "receita") as "receita" | "despesa" });
  }, [conta]);

  const salvar = async () => {
    if (!form.codigo.trim() || !form.nome.trim()) {
      toast("Informe código e nome da conta", "error");
      return;
    }
    const payload: ContaPlanoPayload = { codigo: form.codigo.trim(), nome: form.nome.trim(), tipo: form.tipo };
    try {
      if (conta) await api.atualizarContaPlano(conta.id, payload);
      else await api.criarContaPlano(payload);
      onClose();
      toast("Conta salva", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={conta ? "Editar conta" : "Nova conta"}
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
        <Field label="Código *">
          <Input placeholder="Ex.: 1.01" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
        </Field>
        <Field label="Nome *">
          <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </Field>
        <Field label="Tipo">
          <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value as "receita" | "despesa" })}>
            <option value="receita">Receita</option>
            <option value="despesa">Despesa</option>
          </Select>
        </Field>
      </div>
    </Modal>
  );
}