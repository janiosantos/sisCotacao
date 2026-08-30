// pages/fiscal/ibpt.tsx - módulo Fiscal (Ibpt).

import { useEffect, useState } from "react";
import { api, type IbptItem } from "../../api/client";
import { Button, Cell, EmptyRow, Field, Input, Loading, Table, TBody, THead } from "../../ui/ui";

export function Ibpt() {
  const [ncm, setNcm] = useState("");
  const [rows, setRows] = useState<IbptItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarIbpt({ ncm: ncm.trim() || undefined, limit: 50 }));
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
          <Input
            placeholder="Buscar NCM…"
            value={ncm}
            onChange={(e) => setNcm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-48"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["NCM", "Federal%", "Estadual%", "Municipal%"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={4} message="Nenhum" />
            ) : (
              rows.map((i) => (
                <tr key={i.id} className="hover:bg-gray-50">
                  <Cell className="font-mono">{i.ncm}</Cell>
                  <Cell>{i.aliquota_federal}%</Cell>
                  <Cell>{i.aliquota_estadual}%</Cell>
                  <Cell>{i.aliquota_municipal}%</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}


