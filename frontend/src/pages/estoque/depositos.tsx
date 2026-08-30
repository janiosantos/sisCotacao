// pages/estoque/depositos.tsx - módulo Estoque (Depositos).

import { useState } from "react";
import { api, type Deposito } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, Field, Input, Modal, Table, TBody, THead } from "../../ui/ui";

export function Depositos({ depositos, onUpdate }: { depositos: Deposito[]; onUpdate: () => void }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Deposito | null>(null);
  const [nome, setNome] = useState("");

  const abrir = (d: Deposito | null) => {
    setEditando(d);
    setNome(d?.nome ?? "");
    setModalOpen(true);
  };

  const salvar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      if (editando) await api.atualizarDeposito(editando.id, nome.trim());
      else await api.criarDeposito(nome.trim());
      setModalOpen(false);
      toast(editando ? "Depósito atualizado" : "Depósito criado", "success");
      onUpdate();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (d: Deposito) => {
    try {
      await api.alternarAtivoDeposito(d.id, !d.ativo);
      onUpdate();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => abrir(null)}>
          Novo depósito
        </Button>
      </div>
      <Table>
        <THead cols={["Nome", "Ativo", "Criado em", ""]} />
        <TBody>
          {depositos.map((d) => (
            <tr key={d.id} className="hover:bg-gray-50">
              <Cell className="font-medium">{d.nome}</Cell>
              <Cell>
                <Badge tone={d.ativo ? "green" : "red"}>{d.ativo ? "Ativo" : "Inativo"}</Badge>
              </Cell>
              <Cell className="text-xs text-gray-500">{fmtDate(d.criado_em)}</Cell>
              <Cell>
                <div className="flex justify-end gap-2">
                  <Button size="sm" onClick={() => abrir(d)}>
                    Editar
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => alternar(d)}>
                    {d.ativo ? "Desativar" : "Ativar"}
                  </Button>
                </div>
              </Cell>
            </tr>
          ))}
        </TBody>
      </Table>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar depósito" : "Novo depósito"}
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <Field label="Nome">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
      </Modal>
    </div>
  );
}


