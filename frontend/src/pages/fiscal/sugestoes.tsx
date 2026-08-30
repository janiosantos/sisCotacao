// pages/fiscal/sugestoes.tsx - módulo Fiscal (Sugestoes).

import { useEffect, useState } from "react";
import { api, type SugestaoIbpt } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Select, Table, TBody, THead } from "../../ui/ui";

export function Sugestoes() {
  const [status, setStatus] = useState("pendente");
  const [conf, setConf] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<SugestaoIbpt[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      const confianca_min = parseFloat(conf) || undefined;
      setRows(await api.listarSugestoesIbpt({ status, confianca_min, q: q.trim() || undefined, limit: 200 }));
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

  const revisar = async (id: number, s: "aplicada" | "rejeitada", msg: string) => {
    try {
      await api.revisarSugestaoIbpt(id, s);
      toast(msg, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const gerar = async () => {
    const confianca_min = parseFloat(conf || "40") || 40;
    try {
      const r = await api.gerarSugestoesIbpt({ confianca_min });
      toast(`${r.sugestoes} sugestões geradas`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const aplicarTodas = async () => {
    const confianca_min = parseFloat(conf || "0") || 0;
    if (!window.confirm(`Aplicar TODAS as sugestões pendentes com confiança ≥ ${confianca_min}%?`)) return;
    try {
      const r = await api.aplicarSugestoesIbpt({ confianca_min });
      toast(`${r.aplicadas} NCMs aplicadas`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Status">
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-36">
            <option value="pendente">Pendentes</option>
            <option value="aplicada">Aplicadas</option>
            <option value="rejeitada">Rejeitadas</option>
            <option value="">Todas</option>
          </Select>
        </Field>
        <Field label="Confiança mín. %">
          <Input type="number" min={0} max={100} step={1} placeholder="ex.: 50" value={conf} onChange={(e) => setConf(e.target.value)} className="w-28" />
        </Field>
        <Field label="Busca">
          <Input
            placeholder="Produto, SKU, NCM…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-56"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
        <Button variant="primary" onClick={() => void gerar()}>
          Gerar sugestões
        </Button>
        <Button onClick={() => void aplicarTodas()}>Aplicar pendentes ≥ X%</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "NCM sugerido", "Descrição IBPT", "Confiança", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhuma sugestão" />
            ) : (
              rows.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{s.produto_nome}</span>
                    {s.sku ? <div className="font-mono text-xs text-gray-400">{s.sku}</div> : null}
                  </Cell>
                  <Cell className="font-mono font-semibold">{s.ncm}</Cell>
                  <Cell className="text-xs text-gray-500">{s.descricao || "—"}</Cell>
                  <Cell>
                    <Badge tone={s.confianca >= 70 ? "green" : s.confianca >= 40 ? "gray" : "red"}>{s.confianca.toFixed(0)}%</Badge>
                  </Cell>
                  <Cell>
                    <Badge tone={s.status === "aplicada" ? "green" : s.status === "rejeitada" ? "red" : "gray"}>{s.status}</Badge>
                  </Cell>
                  <Cell>
                    {s.status === "pendente" ? (
                      <div className="flex justify-end gap-2">
                        <Button size="sm" onClick={() => void revisar(s.id, "aplicada", "NCM aplicada")}>
                          Aplicar
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => void revisar(s.id, "rejeitada", "Sugestão rejeitada")}>
                          Rejeitar
                        </Button>
                      </div>
                    ) : null}
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

