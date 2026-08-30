// pages/estoque/expedicao.tsx - módulo Estoque (Expedicao).

import { useEffect, useState } from "react";
import { api, type Deposito, type Expedicao } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, Select, Table, TBody, THead, Textarea } from "../../ui/ui";

export function Expedicao() {
  const [rows, setRows] = useState<Expedicao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ codigo: "", deposito_id: "", transportadora: "", observacao: "" });
  const [depositos, setDepositos] = useState<Deposito[]>([]);

  const carregar = async () => {
    try {
      setRows(await api.listarExpedicao());
      setDepositos(await api.listarDepositos());
    } catch {
      /* silêncio */
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarExpedicao({
        codigo: form.codigo.trim(),
        deposito_id: Number(form.deposito_id),
        transportadora: form.transportadora.trim() || undefined,
        observacao: form.observacao.trim() || undefined,
      });
      setModalOpen(false);
      toast("Expedição criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const statusTone = (s: string) => (s === "finalizado" ? "green" : "gray");

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Nova expedição
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Código", "Depósito", "Data", "Transportadora", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhuma" />
            ) : (
              rows.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{e.codigo}</Cell>
                  <Cell>{e.deposito_nome}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(e.data_expedicao)}</Cell>
                  <Cell>{e.transportadora || "—"}</Cell>
                  <Cell>
                    <Badge tone={statusTone(e.status)}>{e.status}</Badge>
                  </Cell>
                  <Cell>
                    <Select
                      value={e.status}
                      onChange={(ev) => void api.atualizarStatusExpedicao(e.id, ev.target.value).then(carregar)}
                      className="w-36 py-1 text-xs"
                    >
                      {["pendente", "separando", "conferido", "carregado", "finalizado"].map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </Select>
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
        title="Nova expedição"
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
            <Input placeholder="EXP-001" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
          </Field>
          <Field label="Depósito">
            <Select value={form.deposito_id} onChange={(e) => setForm({ ...form, deposito_id: e.target.value })}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Transportadora">
            <Input value={form.transportadora} onChange={(e) => setForm({ ...form, transportadora: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}


