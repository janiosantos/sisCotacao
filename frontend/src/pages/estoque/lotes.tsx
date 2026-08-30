// pages/estoque/lotes.tsx - módulo Estoque (Lotes).

import { useEffect, useState } from "react";
import { api, type Deposito, type LoteItem, type LotePayload } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Cell, EmptyRow, Field, Input, Loading, Modal, Select, Table, TBody, THead } from "../../ui/ui";

export function Lotes({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<LoteItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ deposito_id: "", variante_id: "", codigo: "", quantidade: "", fabricacao: "", validade: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarLotes());
    } catch {
      toast("Erro ao carregar lotes", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    const payload: LotePayload = {
      deposito_id: Number(form.deposito_id),
      variante_id: Number(form.variante_id),
      codigo: form.codigo.trim(),
      quantidade: parseFloat(form.quantidade.replace(",", ".")),
      data_fabricacao: form.fabricacao || undefined,
      data_validade: form.validade || undefined,
    };
    if (!payload.deposito_id || !payload.variante_id || !payload.codigo) {
      toast("Preencha depósito, produto e código do lote", "error");
      return;
    }
    try {
      await api.criarLote(payload);
      setModalOpen(false);
      toast("Lote criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo lote
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "Lote", "Depósito", "Qtd", "Fabricação", "Validade"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhum lote" />
            ) : (
              rows.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{l.produto_nome}</span>
                    <div className="text-xs text-gray-400">{l.sku}</div>
                  </Cell>
                  <Cell className="font-mono text-xs">{l.codigo}</Cell>
                  <Cell>{l.deposito_nome}</Cell>
                  <Cell className="font-medium">{l.quantidade}</Cell>
                  <Cell className="text-xs text-gray-500">{l.data_fabricacao ? fmtDate(l.data_fabricacao) : "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{l.data_validade ? fmtDate(l.data_validade) : "—"}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo lote"
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
          <Field label="Depósito">
            <Select value={form.deposito_id} onChange={(e) => setForm({ ...form, deposito_id: e.target.value })}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Produto (ID)">
            <Input type="number" min={1} value={form.variante_id} onChange={(e) => setForm({ ...form, variante_id: e.target.value })} />
          </Field>
          <Field label="Código do lote">
            <Input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} />
          </Field>
          <Field label="Quantidade">
            <Input type="number" min={0} step="any" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Fabricação">
              <Input type="date" value={form.fabricacao} onChange={(e) => setForm({ ...form, fabricacao: e.target.value })} />
            </Field>
            <Field label="Validade">
              <Input type="date" value={form.validade} onChange={(e) => setForm({ ...form, validade: e.target.value })} />
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  );
}


