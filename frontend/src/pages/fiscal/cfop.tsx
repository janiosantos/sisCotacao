// pages/fiscal/cfop.tsx - módulo Fiscal (Cfop).

import { useEffect, useState } from "react";
import { api, type CfopCode } from "../../api/client";
import { Badge, Button, Cell, EmptyRow, Field, Loading, Select, Table, TBody, THead } from "../../ui/ui";

export function Cfop() {
  const [tipo, setTipo] = useState("");
  const [rows, setRows] = useState<CfopCode[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarCfop(tipo.trim() || undefined));
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
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)} className="w-44">
            <option value="">Todos</option>
            <option value="entrada">Entrada</option>
            <option value="saida">Saída</option>
            <option value="mesma_uf">Mesma UF</option>
            <option value="outra_uf">Outra UF</option>
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Código", "Descrição", "Tipo"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={3} message="Nenhum CFOP" />
            ) : (
              rows.map((c) => (
                <tr key={c.codigo} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                  <Cell>{c.descricao}</Cell>
                  <Cell>
                    <Badge>{c.tipo}</Badge>
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


