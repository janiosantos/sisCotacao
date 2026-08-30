// pages/fiscal/cst.tsx - módulo Fiscal (Cst).

import { useEffect, useState } from "react";
import { api, type CstCode } from "../../api/client";
import { Button, Cell, EmptyRow, Field, Loading, Select, Table, TBody, THead } from "../../ui/ui";

export function Cst() {
  const [tab, setTab] = useState("cst_icms");
  const [rows, setRows] = useState<CstCode[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarCst(tab));
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
        <Field label="Tabela">
          <Select value={tab} onChange={(e) => setTab(e.target.value)} className="w-44">
            <option value="cst_icms">ICMS</option>
            <option value="cst_pis">PIS</option>
            <option value="cst_cofins">COFINS</option>
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Código", "Descrição"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={2} message="Nenhum CST" />
            ) : (
              rows.map((c) => (
                <tr key={c.codigo} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                  <Cell>{c.descricao}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}


