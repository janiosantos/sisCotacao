// pages/compras/lista-cotacoes.tsx — aba Cotações (status normalizado + badge).
import { useEffect, useState } from "react";
import { api, type CotacaoLista } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { Badge, Button, Cell, Loading, Table, TBody, THead } from "../../ui/ui";

const STATUS_COT_LABEL: Record<string, string> = {
  aberta: "Pendente",
  pendente: "Pendente",
  analise: "Em análise",
  fechada: "Finalizada",
  finalizada: "Finalizada",
  cancelada: "Cancelada",
};

function statusCotTone(s: string): "green" | "red" | "amber" | "gray" {
  if (s === "finalizada" || s === "fechada") return "green";
  if (s === "cancelada") return "red";
  if (s === "analise") return "amber";
  return "gray";
}

export function ListaCotacoes({ onNova, onAbrirCompra }: { onNova: () => void; onAbrirCompra: (id: number) => void }) {
  const [cotacoes, setCotacoes] = useState<CotacaoLista[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    void api
      .listarCotacoes("")
      .then(setCotacoes)
      .catch(() => setCotacoes([]))
      .finally(() => setCarregando(false));
  }, []);

  if (carregando) return <Loading />;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Cotações</h3>
        <Button size="sm" variant="primary" onClick={onNova}>
          + Nova cotação
        </Button>
      </div>
      {cotacoes.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">Nenhuma cotação ainda.</p>
      ) : (
        <Table>
          <THead cols={["Nº", "Título", "Status", "Respostas", "Criada em", ""]} />
          <TBody>
            {cotacoes.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <Cell className="font-mono">{c.numero}</Cell>
                <Cell>{c.titulo || "—"}</Cell>
                <Cell>
                  <Badge tone={statusCotTone(c.status)}>{STATUS_COT_LABEL[c.status] || c.status}</Badge>
                </Cell>
                <Cell className="text-xs">
                  {c.n_respostas} / {c.n_fornecedores}
                </Cell>
                <Cell className="text-xs text-gray-500">{fmtDate(c.criado_em)}</Cell>
                <Cell>
                  <div className="flex justify-end">
                    <Button size="sm" onClick={() => onAbrirCompra(c.id)}>
                      Abrir
                    </Button>
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}