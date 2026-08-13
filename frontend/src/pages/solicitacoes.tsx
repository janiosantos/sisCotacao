// pages/solicitacoes.tsx — solicitações de compra (React + Tailwind).

import { useEffect, useState } from "react";
import { api } from "../api/client";
import { fmtDate } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Field, Input, Loading, Modal, PageHeader, Table, TBody, THead, Textarea } from "../ui/ui";

interface Solicitacao {
  id: number;
  codigo: string;
  descricao: string;
  data_solicitacao: string;
  usuario_nome: string | null;
  status: string;
}

export default function Solicitacoes() {
  const [solicitacoes, setSolicitacoes] = useState<Solicitacao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ codigo: "", descricao: "", observacao: "" });

  const carregar = async () => {
    try {
      setSolicitacoes(await api.listarSolicitacoesCompra());
    } catch {
      toast("Erro ao carregar solicitações", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarSolicitacaoCompra({
        codigo: form.codigo.trim(),
        descricao: form.descricao.trim() || undefined,
        observacao: form.observacao.trim() || undefined,
      });
      setModalOpen(false);
      toast("Solicitação criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const statusTone = (s: string) =>
    s === "aprovada" ? "green" : s === "rejeitada" ? "red" : "amber";

  return (
    <div>
      <PageHeader
        title="Solicitações de Compra"
        subtitle="Solicitações internas com aprovação."
        actions={
          <Button variant="primary" onClick={() => setModalOpen(true)}>
            Nova solicitação
          </Button>
        }
      />
      {carregando ? (
        <Loading />
      ) : solicitacoes.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhuma solicitação.
        </div>
      ) : (
        <Table>
          <THead cols={["Código", "Descrição", "Data", "Solicitante", "Status"]} />
          <TBody>
            {solicitacoes.map((s) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <Cell className="font-mono font-semibold">{s.codigo}</Cell>
                <Cell>{s.descricao}</Cell>
                <Cell className="text-xs text-gray-500">{fmtDate(s.data_solicitacao)}</Cell>
                <Cell>{s.usuario_nome || "—"}</Cell>
                <Cell>
                  <Badge tone={statusTone(s.status)}>{s.status}</Badge>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nova solicitação"
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
            <Input placeholder="SOL-001" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
          </Field>
          <Field label="Descrição">
            <Textarea value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
