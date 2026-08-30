// pages/fiscal/historico.tsx - módulo Fiscal (HistoricoFiscal).

import { useEffect, useState } from "react";
import { api, type HistoricoFiscalItem } from "../../api/client";
import { fmtDateTime } from "../../ui/format";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Table, TBody, THead } from "../../ui/ui";

export function HistoricoFiscal() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<HistoricoFiscalItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarHistoricoFiscal({ q: q.trim() || undefined }));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Busca">
          <Input
            placeholder="Produto, SKU, NCM…"
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
          <THead cols={["Data", "Produto", "Tipo", "NCM", "CEST", "CSOSN", "ICMS%", "ST%", "MVA%", "Por"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={10} message="Nenhum registro" />
            ) : (
              rows.map((h) => (
                <tr key={h.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDateTime(h.criado_em)}</Cell>
                  <Cell>
                    <span className="font-medium">{h.produto_nome}</span>
                    {h.sku ? <div className="font-mono text-xs text-gray-400">{h.sku}</div> : null}
                  </Cell>
                  <Cell>
                    <Badge tone={h.tipo === "criado" ? "gray" : "green"}>{h.tipo}</Badge>
                  </Cell>
                  <Cell className="font-mono text-xs">{h.ncm || "—"}</Cell>
                  <Cell className="font-mono text-xs">{h.cest || "—"}</Cell>
                  <Cell className="text-xs">{h.csosn || "—"}</Cell>
                  <Cell>{h.aliquota_icms ? h.aliquota_icms + "%" : "—"}</Cell>
                  <Cell>{h.aliquota_icms_st ? h.aliquota_icms_st + "%" : "—"}</Cell>
                  <Cell>{h.mva ? h.mva + "%" : "—"}</Cell>
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


