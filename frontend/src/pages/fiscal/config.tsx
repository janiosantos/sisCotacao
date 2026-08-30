// pages/fiscal/config.tsx - módulo Fiscal (Config).

import { useEffect, useState } from "react";
import { api, type FiscalConfigItem } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Cell, EmptyRow, Field, Input, Loading, Table, TBody, THead } from "../../ui/ui";
import { ModalFiscal } from "./modal-fiscal";

export function Config() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<FiscalConfigItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [editando, setEditando] = useState<FiscalConfigItem | null>(null);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarFiscalConfig({ q: q.trim() || undefined, limit: 200 }));
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

  const gerar = async () => {
    try {
      const r = await api.gerarFiscalConfig();
      toast(`${r.gerados} configurações geradas`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => void gerar()}>
          Gerar config padrão
        </Button>
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
          <THead cols={["Produto", "NCM", "CFOP", "CST ICMS", "PIS", "COFINS", "ICMS%", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhuma config" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{c.produto_nome}</span>
                    {c.sku ? <div className="font-mono text-xs text-gray-400">{c.sku}</div> : null}
                  </Cell>
                  <Cell className="font-mono text-xs">{c.ncm || "—"}</Cell>
                  <Cell className="font-mono text-xs">{c.cfop ?? "—"}</Cell>
                  <Cell className="text-xs">{c.cst_icms ?? "—"}</Cell>
                  <Cell className="text-xs">{c.cst_pis ?? "—"}</Cell>
                  <Cell className="text-xs">{c.cst_cofins ?? "—"}</Cell>
                  <Cell>{c.aliquota_icms ? c.aliquota_icms + "%" : "—"}</Cell>
                  <Cell>
                    <div className="flex justify-end">
                      <Button size="sm" variant="ghost" onClick={() => setEditando(c)}>
                        Editar
                      </Button>
                    </div>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <ModalFiscal
        config={editando}
        onClose={() => setEditando(null)}
        onSaved={() => void carregar()}
      />
    </div>
  );
}


