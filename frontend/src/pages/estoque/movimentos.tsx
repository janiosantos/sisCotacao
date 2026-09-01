// pages/estoque/movimentos.tsx - módulo Estoque (Movimentos).

import { useEffect, useState } from "react";
import { api, type Deposito, type MovimentoItem, type MovimentoPayload } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, Select, Table, TBody, THead, Textarea } from "../../ui/ui";

export function Movimentos({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<MovimentoItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [dep, setDep] = useState("");
  const [tipo, setTipo] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ deposito_id: "", tipo: "entrada", produto_id: "", quantidade: "", documento: "", observacao: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarMovimentos({ deposito_id: dep || undefined, tipo: tipo || undefined }));
    } catch {
      toast("Erro ao carregar movimentos", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const registrar = async () => {
    const payload: MovimentoPayload = {
      deposito_id: Number(form.deposito_id),
      tipo: form.tipo as MovimentoPayload["tipo"],
      produto_id: Number(form.produto_id),
      quantidade: parseFloat(form.quantidade.replace(",", ".")),
      documento: form.documento.trim() || undefined,
      observacao: form.observacao.trim() || undefined,
    };
    if (!payload.deposito_id || !payload.produto_id || payload.quantidade <= 0) {
      toast("Preencha depósito, produto e quantidade", "error");
      return;
    }
    try {
      await api.registrarMovimento(payload);
      setModalOpen(false);
      toast("Movimento registrado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Registrar movimento
        </Button>
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-44">
            <option value="">Todos</option>
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)} className="w-36">
            <option value="">Todos</option>
            <option value="entrada">Entrada</option>
            <option value="saida">Saída</option>
            <option value="ajuste">Ajuste</option>
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Produto", "Depósito", "Tipo", "Qtd", "Saldo ant.", "Saldo novo", "Doc"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhum movimento" />
            ) : (
              rows.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDate(m.criado_em)}</Cell>
                  <Cell>
                    <span className="font-medium">{m.produto_nome}</span>
                    <div className="text-xs text-gray-400">{m.sku}</div>
                  </Cell>
                  <Cell>{m.deposito_nome}</Cell>
                  <Cell>
                    <Badge tone={m.tipo === "entrada" ? "green" : m.tipo === "saida" ? "red" : "gray"}>{m.tipo}</Badge>
                  </Cell>
                  <Cell className="font-medium">{m.quantidade}</Cell>
                  <Cell className="text-xs text-gray-500">{m.saldo_anterior}</Cell>
                  <Cell className="text-xs text-gray-500">{m.saldo_posterior}</Cell>
                  <Cell className="font-mono text-xs">{m.documento || ""}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Registrar movimento"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void registrar()}>
              Registrar
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
          <Field label="Tipo">
            <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="entrada">Entrada</option>
              <option value="saida">Saída</option>
              <option value="ajuste">Ajuste</option>
            </Select>
          </Field>
          <Field label="Produto (ID)">
            <Input type="number" min={1} value={form.produto_id} onChange={(e) => setForm({ ...form, produto_id: e.target.value })} />
          </Field>
          <Field label="Quantidade">
            <Input type="number" min="0.01" step="any" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: e.target.value })} />
          </Field>
          <Field label="Documento">
            <Input value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}


