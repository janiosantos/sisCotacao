// pages/plano_contas.tsx — plano de contas (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type ContaPlano } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ModalContaForm } from "./plano_contas/modal-form";

export default function PlanoContas() {
  const [contas, setContas] = useState<ContaPlano[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<ContaPlano | null>(null);

  const carregar = async () => {
    try {
      setContas(await api.listarPlanoContas());
    } catch (e) {
      toast("Erro ao carregar plano de contas: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (c: ContaPlano | null) => {
    setEditando(c);
    setModalOpen(true);
  };

  const alternar = async (c: ContaPlano) => {
    try {
      await api.alternarAtivoContaPlano(c.id, !c.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <PageHeader
        title="Plano de contas"
        subtitle="Contas para classificar receitas e despesas do negócio."
        actions={
          <Button variant="primary" onClick={() => abrir(null)}>
            + Nova conta
          </Button>
        }
      />
      {carregando ? (
        <Loading />
      ) : contas.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhuma conta cadastrada.
        </div>
      ) : (
        <Table>
          <THead cols={["Código", "Nome", "Tipo", "Status", ""]} />
          <TBody>
            {contas.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <Cell className="font-mono text-xs">{c.codigo}</Cell>
                <Cell className="font-medium">{c.nome}</Cell>
                <Cell>
                  <Badge tone={c.tipo === "receita" ? "green" : "amber"}>{c.tipo}</Badge>
                </Cell>
                <Cell>
                  <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativo" : "Inativo"}</Badge>
                </Cell>
                <Cell>
                  <div className="flex justify-end gap-2">
                    <Button size="sm" onClick={() => abrir(c)}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => alternar(c)}>
                      {c.ativo ? "Desativar" : "Ativar"}
                    </Button>
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      {modalOpen && (
        <ModalContaForm
          conta={editando}
          onClose={() => setModalOpen(false)}
          onSaved={carregar}
        />
      )}
    </div>
  );
}
