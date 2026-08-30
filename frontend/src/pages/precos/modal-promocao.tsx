// pages/precos/modal-promocao.tsx - módulo Preços (ModalPromocao).

import { useEffect, useState } from "react";
import { api, type Promocao, type PromocaoPayload } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select } from "../../ui/ui";

export function ModalPromocao({
  editando,
  open,
  onClose,
  onSaved,
}: {
  editando: Promocao | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState("percentual");
  const [valor, setValor] = useState("0");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");

  useEffect(() => {
    if (open) {
      setNome(editando?.nome ?? "");
      setTipo(editando?.tipo ?? "percentual");
      setValor(String(editando?.valor ?? 0));
      setInicio(editando?.data_inicio ?? "");
      setFim(editando?.data_fim ?? "");
    }
  }, [open, editando]);

  const salvar = async () => {
    const payload: PromocaoPayload = {
      nome: nome.trim(),
      tipo,
      valor: parseFloat(valor.replace(",", ".")),
      data_inicio: inicio || undefined,
      data_fim: fim || undefined,
    };
    if (!payload.nome) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      if (editando) await api.atualizarPromocao(editando.id, payload);
      else await api.criarPromocao(payload);
      toast(editando ? "Promoção atualizada" : "Promoção criada", "success");
      onClose();
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editando ? "Editar promoção" : "Nova promoção"}
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
        <Field label="Nome">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Tipo">
            <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
              <option value="percentual">Percentual (%)</option>
              <option value="valor_fixo">Valor fixo (R$)</option>
            </Select>
          </Field>
          <Field label="Valor">
            <Input type="number" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} />
          </Field>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Início">
            <Input type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} />
          </Field>
          <Field label="Fim">
            <Input type="date" value={fim} onChange={(e) => setFim(e.target.value)} />
          </Field>
        </div>
      </div>
    </Modal>
  );
}


