// pages/precos/historico.tsx - módulo Preços (Historico).

import { useEffect, useState } from "react";
import { api, type HistoricoPrecoItem, type TabelaPreco } from "../../api/client";
import { fmtDateTime, fmtMoney } from "../../ui/format";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Select, Table, TBody, THead } from "../../ui/ui";

export function Historico() {
  const [tabelas, setTabelas] = useState<TabelaPreco[]>([]);
  const [filtroTab, setFiltroTab] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<HistoricoPrecoItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      const tabela_id = parseInt(filtroTab, 10) || undefined;
      setRows(await api.listarHistoricoPrecos({ tabela_id, q: q.trim() || undefined }));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void api
      .listarTabelasPreco()
      .then(setTabelas)
      .catch(() => {});
  }, []);

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Tabela">
          <Select value={filtroTab} onChange={(e) => setFiltroTab(e.target.value)} className="w-48">
            <option value="">Todas</option>
            {tabelas.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Busca">
          <Input
            placeholder="Produto, SKU, tabela…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-64"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Produto", "Tabela", "Anterior", "Novo", "Margem", "Origem", "Aprovado por"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhum registro" />
            ) : (
              rows.map((h) => (
                <tr key={h.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDateTime(h.criado_em)}</Cell>
                  <Cell>
                    <span className="font-medium">{h.produto_nome}</span>
                    {h.sku ? <div className="font-mono text-xs text-gray-400">{h.sku}</div> : null}
                  </Cell>
                  <Cell>{h.tabela_nome}</Cell>
                  <Cell>{fmtMoney(h.preco_anterior)}</Cell>
                  <Cell className="font-medium">{fmtMoney(h.preco_novo)}</Cell>
                  <Cell>{h.margem_pct != null ? h.margem_pct.toFixed(2).replace(".", ",") + "%" : "—"}</Cell>
                  <Cell>
                    <Badge>{h.origem || h.tipo}</Badge>
                  </Cell>
                  <Cell>{h.usuario_nome ?? "—"}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}

