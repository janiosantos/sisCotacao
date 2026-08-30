// pages/fiscal/cest.tsx - módulo Fiscal (Cest).

import { useEffect, useState } from "react";
import { api, type CestItem } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { Button, Cell, EmptyRow, Field, Input, Loading, Table, TBody, THead } from "../../ui/ui";

export function Cest() {
  const [ncm, setNcm] = useState("");
  const [rows, setRows] = useState<CestItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarCest(ncm.trim() || undefined));
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
        <Field label="NCM">
          <Input placeholder="Ex.: 8544" value={ncm} onChange={(e) => setNcm(e.target.value)} className="w-48" />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["CEST", "NCM", "Descrição", "Vigência"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={4} message="Nenhum CEST" />
            ) : (
              rows.map((c) => (
                <tr key={c.codigo} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                  <Cell className="font-mono text-xs">{c.ncm_prefix || "—"}</Cell>
                  <Cell>{c.descricao || "—"}</Cell>
                  <Cell className="text-xs">
                    {c.vigencia_inicio ? fmtDate(c.vigencia_inicio) : ""}
                    {c.vigencia_fim ? " → " + fmtDate(c.vigencia_fim) : ""}
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}


