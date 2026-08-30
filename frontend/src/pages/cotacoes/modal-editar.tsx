// pages/cotacoes/modal-editar.tsx - módulo Cotações (ModalEditar).

import { useEffect, useState } from "react";
import { api, type CotacaoLista } from "../../api/client";
import { Button, Field, Input, Modal, Textarea } from "../../ui/ui";

export function ModalEditar({
  cotacao,
  open,
  onClose,
  onSaved,
}: {
  cotacao: CotacaoLista;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [titulo, setTitulo] = useState("");
  const [cliente, setCliente] = useState("");
  const [obs, setObs] = useState("");

  useEffect(() => {
    if (open) {
      setTitulo(cotacao.titulo || "");
      setCliente(cotacao.cliente || "");
      setObs(cotacao.observacoes || "");
    }
  }, [open, cotacao]);

  const salvar = async () => {
    await api.atualizarCotacao(cotacao.id, { titulo: titulo.trim(), cliente: cliente.trim(), observacoes: obs.trim() });
    onSaved();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Editar cotação"
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
        <Field label="Título">
          <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} />
        </Field>
        <Field label="Cliente">
          <Input value={cliente} onChange={(e) => setCliente(e.target.value)} />
        </Field>
        <Field label="Observações">
          <Textarea value={obs} onChange={(e) => setObs(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}


