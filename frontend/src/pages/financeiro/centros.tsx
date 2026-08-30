// pages/financeiro/centros.tsx — centros de custo (CRUD).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Modal, Table, TBody, THead } from "../../ui/ui";

interface CentroCusto {
  id: number;
  codigo: string;
  nome: string;
  ativo: number | boolean;
}

export function Centros() {
  const [rows, setRows] = useState<CentroCusto[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ codigo: "", nome: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarCentrosCusto());
    } catch {
      toast("Erro ao carregar centros", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarCentroCusto({ codigo: form.codigo.trim(), nome: form.nome.trim() });
      setModalOpen(false);
      toast("Centro criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo centro
        </Button>
      </div>
      <Table>
        <THead cols={["Código", "Nome", "Status"]} />
        <TBody>
          {rows.length === 0 ? (
            <EmptyRow colSpan={3} message="Nenhum centro" />
          ) : (
            rows.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                <Cell>{c.nome}</Cell>
                <Cell>
                  <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativo" : "Inativo"}</Badge>
                </Cell>
              </tr>
            ))
          )}
        </TBody>
      </Table>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo centro de custo"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Código">
            <Input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
          </Field>
          <Field label="Nome">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}