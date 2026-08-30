// pages/unidades/modal-form.tsx — criação/edição de unidade de compra.
import { useEffect, useState } from "react";
import { api, type UnidadeCompra } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalUnidadeForm({
  unidade,
  onClose,
  onSaved,
}: {
  unidade: UnidadeCompra | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [sigla, setSigla] = useState("");
  const [descricao, setDescricao] = useState("");

  useEffect(() => {
    setSigla(unidade?.sigla ?? "");
    setDescricao(unidade?.descricao ?? "");
  }, [unidade]);

  const salvar = async () => {
    if (!sigla.trim()) {
      toast("Informe a sigla", "error");
      return;
    }
    try {
      if (unidade) await api.atualizarUnidadeCompra(unidade.id, sigla.trim().toUpperCase(), descricao.trim(), unidade.ativo);
      else await api.criarUnidadeCompra(sigla.trim().toUpperCase(), descricao.trim());
      onClose();
      toast(unidade ? "Unidade atualizada" : "Unidade criada", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={unidade ? "Editar unidade" : "Nova unidade"}
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
        <Field label="Sigla *">
          <Input placeholder="Ex.: CX, PCT, RL" maxLength={10} value={sigla} onChange={(e) => setSigla(e.target.value)} autoFocus />
        </Field>
        <Field label="Descrição">
          <Input placeholder="Ex.: Caixa, Pacote, Rolo" value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}