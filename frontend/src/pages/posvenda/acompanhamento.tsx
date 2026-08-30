// pages/posvenda/acompanhamento.tsx — acompanhamento de clientes (pós-venda).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, Select, Table, TBody, THead, Textarea } from "../../ui/ui";

interface Interacao {
  id: number;
  cliente_nome: string;
  tipo: string;
  descricao: string;
  data_contato: string;
  data_proximo_contato: string | null;
}

export function Acompanhamento() {
  const [rows, setRows] = useState<Interacao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [filtroCliId, setFiltroCliId] = useState("");
  const [pendentes, setPendentes] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ cliente: "", tipo: "ligacao", data: "", desc: "", prox: "", orc: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarInteracoes({ cliente_id: filtroCliId ? Number(filtroCliId) : undefined, pendentes }));
    } catch {
      toast("Erro ao carregar interações", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const salvar = async () => {
    try {
      await api.criarInteracao({
        cliente_nome: form.cliente.trim(),
        tipo: form.tipo,
        data_contato: form.data,
        descricao: form.desc.trim(),
        data_proximo_contato: form.prox || undefined,
        orcamento_id: Number(form.orc) || undefined,
      });
      setModalOpen(false);
      toast("Interação registrada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Nova interação
        </Button>
        <Field label="Cliente ID">
          <Input type="number" value={filtroCliId} onChange={(e) => setFiltroCliId(e.target.value)} className="w-32" />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" className="h-4 w-4 rounded border-gray-300" checked={pendentes} onChange={(e) => setPendentes(e.target.checked)} />
          Pendentes
        </label>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Cliente", "Tipo", "Descrição", "Próx. contato"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={5} message="Nenhuma interação" />
            ) : (
              rows.map((i) => (
                <tr key={i.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDate(i.data_contato)}</Cell>
                  <Cell className="font-medium">{i.cliente_nome}</Cell>
                  <Cell>
                    <Badge tone="gray">{i.tipo}</Badge>
                  </Cell>
                  <Cell>{i.descricao}</Cell>
                  <Cell className="text-xs text-gray-500">{i.data_proximo_contato ? fmtDate(i.data_proximo_contato) : "—"}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nova interação"
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
            <Input placeholder="Nome" value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} autoFocus />
          </Field>
          <Field label="Tipo">
            <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              {["ligacao", "visita", "email", "whatsapp", "follow_up", "outro"].map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Data do contato">
            <Input type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
          </Field>
          <Field label="Descrição">
            <Textarea value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Próximo contato">
              <Input type="date" value={form.prox} onChange={(e) => setForm({ ...form, prox: e.target.value })} />
            </Field>
            <Field label="Orçamento ID">
              <Input type="number" value={form.orc} onChange={(e) => setForm({ ...form, orc: e.target.value })} />
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  );
}