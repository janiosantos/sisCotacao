// pages/financeiro/adiantamentos.tsx — adiantamentos (clientes/fornecedores).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Modal, Select, Table, TBody, THead, Textarea } from "../../ui/ui";

interface Adiantamento {
  id: number;
  tipo: string;
  pessoa_nome: string;
  valor: number;
  saldo: number;
  data_adiantamento: string;
}

export function Adiantamentos() {
  const [rows, setRows] = useState<Adiantamento[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ tipo: "cliente", nome: "", valor: "", data: "", obs: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarAdiantamentos());
    } catch {
      toast("Erro ao carregar adiantamentos", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarAdiantamento({
        tipo: form.tipo,
        pessoa_nome: form.nome.trim(),
        valor: parseFloat(form.valor.replace(",", ".")),
        data_adiantamento: form.data,
        observacao: form.obs.trim() || undefined,
      });
      setModalOpen(false);
      toast("Adiantamento criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo adiantamento
        </Button>
      </div>
      <Table>
        <THead cols={["Tipo", "Pessoa", "Valor", "Saldo", "Data"]} />
        <TBody>
          {rows.length === 0 ? (
            <EmptyRow colSpan={5} message="Nenhum" />
          ) : (
            rows.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50">
                <Cell>
                  <Badge tone="gray">{a.tipo}</Badge>
                </Cell>
                <Cell className="font-medium">{a.pessoa_nome}</Cell>
                <Cell>{fmtMoney(a.valor)}</Cell>
                <Cell className="font-medium">{fmtMoney(a.saldo)}</Cell>
                <Cell className="text-xs text-gray-500">{fmtDate(a.data_adiantamento)}</Cell>
              </tr>
            ))
          )}
        </TBody>
      </Table>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo adiantamento"
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
          <Field label="Tipo">
            <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="cliente">Cliente</option>
              <option value="fornecedor">Fornecedor</option>
            </Select>
          </Field>
          <Field label="Nome">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
          </Field>
          <Field label="Valor">
            <Input type="number" step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
          </Field>
          <Field label="Data">
            <Input type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.obs} onChange={(e) => setForm({ ...form, obs: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}