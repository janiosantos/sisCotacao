// pages/posvenda/garantia.tsx — garantias de produtos (pós-venda).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, Table, TBody, THead, Textarea } from "../../ui/ui";

interface GarantiaRow {
  id: number;
  cliente_nome: string;
  produto_nome: string;
  data_inicio: string;
  data_fim: string;
  dias: number;
  status: string;
}

export function Garantia() {
  const [rows, setRows] = useState<GarantiaRow[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ cliente: "", produto: "", inicio: "", fim: "", dias: "90", desc: "", obs: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarGarantias());
    } catch {
      toast("Erro ao carregar garantias", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarGarantia({
        cliente_nome: form.cliente.trim(),
        produto_nome: form.produto.trim(),
        data_inicio: form.inicio,
        data_fim: form.fim,
        dias: parseInt(form.dias, 10) || 90,
        descricao: form.desc.trim() || undefined,
        observacao: form.obs.trim() || undefined,
      });
      setModalOpen(false);
      toast("Garantia registrada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alterarStatus = async (g: GarantiaRow) => {
    const novos: Record<string, string> = { ativa: "acionada", acionada: "cancelada", cancelada: "ativa", vencida: "ativa" };
    const novo = novos[g.status] || "ativa";
    try {
      await api.atualizarStatusGarantia(g.id, novo);
      toast(`Status alterado para ${novo}`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const statusTone = (s: string) => (s === "ativa" ? "green" : s === "vencida" ? "gray" : "red");

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Nova garantia
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Cliente", "Produto", "Início", "Fim", "Dias", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={7} message="Nenhuma garantia" />
            ) : (
              rows.map((g) => (
                <tr key={g.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{g.cliente_nome}</Cell>
                  <Cell>{g.produto_nome}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(g.data_inicio)}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(g.data_fim)}</Cell>
                  <Cell>{g.dias}</Cell>
                  <Cell>
                    <Badge tone={statusTone(g.status)}>{g.status}</Badge>
                  </Cell>
                  <Cell>
                    <Button size="sm" variant="ghost" onClick={() => alterarStatus(g)}>
                      Alterar status
                    </Button>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nova garantia"
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
          <Field label="Cliente">
            <Input value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} autoFocus />
          </Field>
          <Field label="Produto">
            <Input value={form.produto} onChange={(e) => setForm({ ...form, produto: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Data início">
              <Input type="date" value={form.inicio} onChange={(e) => setForm({ ...form, inicio: e.target.value })} />
            </Field>
            <Field label="Data fim">
              <Input type="date" value={form.fim} onChange={(e) => setForm({ ...form, fim: e.target.value })} />
            </Field>
          </div>
          <Field label="Dias">
            <Input type="number" value={form.dias} onChange={(e) => setForm({ ...form, dias: e.target.value })} />
          </Field>
          <Field label="Descrição">
            <Textarea value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.obs} onChange={(e) => setForm({ ...form, obs: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}