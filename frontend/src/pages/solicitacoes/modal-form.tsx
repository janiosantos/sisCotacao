// pages/solicitacoes/modal-form.tsx — criação de solicitação de compra.
import { useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Textarea } from "../../ui/ui";

export function ModalSolicitacaoForm({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({ codigo: "", descricao: "", observacao: "" });

  const salvar = async () => {
    try {
      await api.criarSolicitacaoCompra({
        codigo: form.codigo.trim(),
        descricao: form.descricao.trim() || undefined,
        observacao: form.observacao.trim() || undefined,
      });
      onClose();
      toast("Solicitação criada", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Nova solicitação"
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
        <Field label="Código">
          <Input placeholder="SOL-001" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
        </Field>
        <Field label="Descrição">
          <Textarea value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
        </Field>
        <Field label="Observação">
          <Textarea value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
        </Field>
      </div>
    </Modal>
  );
}