// pages/precos/modal-tabela.tsx - módulo Preços (ModalTabela).

import { useEffect, useState } from "react";
import { api, type TabelaPreco, type TabelaPrecoPayload } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select } from "../../ui/ui";

export function ModalTabela({
  editando,
  open,
  onClose,
  onSaved,
}: {
  editando: TabelaPreco | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState("varejo");
  const [margem, setMargem] = useState("0");
  const [markup, setMarkup] = useState("0");
  const [metodologia, setMetodologia] = useState<"divisor" | "markup_custo">("divisor");

  useEffect(() => {
    if (open) {
      setNome(editando?.nome ?? "");
      setTipo(editando?.tipo ?? "varejo");
      setMargem(String(editando?.margem_padrao ?? 0));
      setMarkup(String(editando?.markup ?? 0));
      setMetodologia(editando?.metodologia ?? "divisor");
    }
  }, [open, editando]);

  const salvar = async () => {
    const payload: TabelaPrecoPayload = {
      nome: nome.trim(),
      tipo,
      margem_padrao: parseFloat(margem.replace(",", ".")),
      markup: parseFloat(markup.replace(",", ".")),
      metodologia,
    };
    if (!payload.nome) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      if (editando) await api.atualizarTabelaPreco(editando.id, payload);
      else await api.criarTabelaPreco(payload);
      toast(editando ? "Tabela atualizada" : "Tabela criada", "success");
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
      title={editando ? "Editar tabela" : "Nova tabela"}
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
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="varejo">varejo</option>
            <option value="atacado">atacado</option>
            <option value="contrato">contrato</option>
            <option value="promocional">promocional</option>
          </Select>
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Margem % sobre a venda">
            <Input type="number" step="0.1" value={margem} onChange={(e) => setMargem(e.target.value)} />
          </Field>
          <Field label="Markup % sobre o custo (legado)">
            <Input type="number" step="0.1" value={markup} onChange={(e) => setMarkup(e.target.value)} />
          </Field>
        </div>
        <Field label="Método de formação">
          <Select value={metodologia} onChange={(e) => setMetodologia(e.target.value as "divisor" | "markup_custo")}>
            <option value="divisor">Markup divisor (recomendado)</option>
            <option value="markup_custo">Markup sobre o custo (compatibilidade)</option>
          </Select>
        </Field>
        <p className="rounded-md bg-brand-50 px-3 py-2 text-xs leading-5 text-brand-800">
          O método divisor considera despesas, impostos, taxas e margem sobre o preço de venda. Use o método legado apenas quando a política comercial da tabela já estiver definida como acréscimo sobre o custo.
        </p>
      </div>
    </Modal>
  );
}


