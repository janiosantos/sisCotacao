// pages/estoque/saldo.tsx - módulo Estoque (Saldo).

import { useEffect, useState } from "react";
import { api, type Deposito, type SaldoItem } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Paginacao, Select, Table, TBody, THead } from "../../ui/ui";

export function Saldo({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<SaldoItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [dep, setDep] = useState("");
  const [q, setQ] = useState("");
  const [familia, setFamilia] = useState("");
  const [pagina, setPagina] = useState(1);
  const POR_PAGINA = 50;

const [familias, setFamilias] = useState<{ id: number; nome: string }[]>([]);
  const [valorizacao, setValorizacao] = useState<{ total: number; data_corte?: string | null } | null>(null);
  useEffect(() => {
    void api.listarFamilias().then(setFamilias).catch(() => {});
  }, []);

  const buscar = async () => {
    setCarregando(true);
    try {
      setRows(
        await api.saldoEstoque({ deposito_id: dep || undefined, familia_id: familia || undefined, q: q || undefined })
      );
    } catch {
      toast("Erro ao carregar saldo", "error");
    } finally {
      setCarregando(false);
    }
    if (dep) {
      try {
        setValorizacao(await api.valorizacaoEstoque(Number(dep)));
      } catch {
        setValorizacao(null);
      }
    } else {
      setValorizacao(null);
    }
  };

  useEffect(() => {
    void buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-48">
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Família">
          <Select value={familia} onChange={(e) => setFamilia(e.target.value)} className="w-48">
            <option value="">Todas</option>
            {familias.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Busca">
          <Input placeholder="Produto, SKU, marca…" value={q} onChange={(e) => setQ(e.target.value)} className="w-64" />
        </Field>
        <Button variant="primary" onClick={() => void buscar()}>
          Filtrar
        </Button>
      </div>

{valorizacao ? (
        <div className="mb-3 flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3">
          <div className="text-sm text-gray-600">
            <span className="font-semibold text-gray-800">Valorização do estoque</span>
            <span className="ml-2 text-xs text-gray-400">quantidade × custo médio</span>
          </div>
          <div className="text-lg font-bold text-emerald-700">{fmtMoney(valorizacao.total)}</div>
        </div>
      ) : null}

      {carregando ? (
<Loading />
      ) : (
        <>
        <Table>
<THead cols={["Produto", "SKU", "Família", "Depósito", "Unid.", "Emb.", "Físico", "Reservado", "Disponível", "Custo médio", "Situação", "Preço", "NCM", "Localização", "Atualizado"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={15} message="Nenhum saldo encontrado" />
            ) : (
              rows.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA).map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{s.produto_nome}</span>
                    {s.marca ? <div className="text-xs text-gray-400">{s.marca}</div> : null}
                  </Cell>
                  <Cell className="font-mono text-xs">{s.sku}</Cell>
                  <Cell className="text-xs text-gray-500">{s.familia_nome || "—"}</Cell>
                  <Cell>{s.deposito_nome}</Cell>
                  <Cell className="text-xs">{s.unidade_venda || "UN"}</Cell>
                  <Cell className="text-xs">{s.embalagem ? `${s.embalagem}/cx` : "—"}</Cell>
                  <Cell className="font-medium">{s.quantidade}</Cell>
                  <Cell className="text-xs">{s.reserva > 0 ? s.reserva : "—"}</Cell>
                  <Cell className="font-medium text-emerald-700">{s.disponivel ?? s.quantidade - s.reserva}</Cell>
                  <Cell className="text-xs text-gray-500">{s.custo_medio ? fmtMoney(s.custo_medio) : "—"}</Cell>
                  <Cell>
                    {s.situacao === "ruptura" ? <Badge tone="red">ruptura</Badge> : s.situacao === "excesso" ? <Badge tone="amber">excesso</Badge> : <span className="text-xs text-gray-400">ok</span>}
                  </Cell>
                  <Cell>{fmtMoney(s.preco)}</Cell>
                  <Cell className="font-mono text-xs">{s.ncm || "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{s.localizacao || "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(s.atualizado_em)}</Cell>
                </tr>
              ))
            )}
</TBody>
        </Table>
        <Paginacao total={rows.length} pagina={pagina} porPagina={POR_PAGINA} onChange={setPagina} />
        </>
      )}
    </div>
  );
}


