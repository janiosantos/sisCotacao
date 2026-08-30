// pages/solicitacoes.tsx — solicitações de compra (React + Tailwind).

import { useEffect, useState } from "react";
import { api } from "../api/client";
import { fmtDate } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ModalSolicitacaoForm } from "./solicitacoes/modal-form";

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

      {modalOpen && (
        <ModalSolicitacaoForm
          onClose={() => setModalOpen(false)}
          onSaved={carregar}
        />
      )}
    </div>
  );
}
