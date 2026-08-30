// pages/precos/modal-criar-revisao.tsx - módulo Preços (ModalCriarRevisao).

import { useEffect, useState } from "react";
import { api, type TabelaPreco } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select } from "../../ui/ui";

export function ModalCriarRevisao({
  tabelas,
  open,
  onClose,
  onSaved,
}: {
  tabelas: TabelaPreco[];
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [tabelaId, setTabelaId] = useState("");
  const [codigo, setCodigo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [cliente, setCliente] = useState("");
  const [validade, setValidade] = useState("");

  useEffect(() => {
    if (open) {
      setTabelaId(tabelas[0] ? String(tabelas[0].id) : "");
      setCodigo("");
      setDescricao("");
      setCliente("");
      setValidade("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const salvar = async () => {
    try {
      await api.criarRevisaoPreco({
        tabela_id: parseInt(tabelaId, 10),
        codigo: codigo.trim(),
        descricao: descricao.trim() || undefined,
        cliente_id: parseInt(cliente, 10) || undefined,
        data_validade: validade || undefined,
      });
      toast("Revisão criada", "success");
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
      title="Nova revisão"
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
        <Field label="Tabela">
          <Select value={tabelaId} onChange={(e) => setTabelaId(e.target.value)}>
            {tabelas.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Código">
          <Input placeholder="Ex.: REV-001" value={codigo} onChange={(e) => setCodigo(e.target.value)} />
        </Field>
        <Field label="Descrição">
          <Input placeholder="Ex.: Preços Iniciais" value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </Field>
        <Field label="Cliente (ID, opcional)">
          <Input type="number" min={1} placeholder="ID do cliente" value={cliente} onChange={(e) => setCliente(e.target.value)} />
        </Field>
        <Field label="Data validade (opcional)">
          <Input type="date" value={validade} onChange={(e) => setValidade(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}


