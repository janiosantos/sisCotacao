// pages/posvenda/devolucao.tsx — devolução / troca de produtos (pós-venda).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, Field, Input, Select, Table, TBody, THead } from "../../ui/ui";

interface DevolucaoRow {
  id: number;
  orcamento_id: number | null;
  produto_nome: string;
  sku: string;
  quantidade: number;
  motivo: string;
  tipo: string;
  status: string;
  criado_em: string;
}

export function Devolucao() {
  const [rows, setRows] = useState<DevolucaoRow[]>([]);
  const [form, setForm] = useState({ orc: "", var: "", qtd: "1", tipo: "devolucao", motivo: "" });

  const carregar = async () => {
    try {
      setRows((await api.listarDevolucoes()) as DevolucaoRow[]);
    } catch {
      toast("Erro ao carregar devoluções", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const registrar = async () => {
    const produto_id = parseInt(form.var, 10);
    const quantidade = parseFloat(form.qtd);
    if (!produto_id || quantidade <= 0) {
      toast("Informe produto e quantidade", "error");
      return;
    }
    try {
      await api.registrarDevolucao({
        orcamento_id: parseInt(form.orc, 10) || undefined,
        produto_id,
        quantidade,
        tipo: form.tipo,
        motivo: form.motivo.trim(),
      });
      toast("Devolução registrada (estoque atualizado)", "success");
      setForm({ orc: "", var: "", qtd: "1", tipo: "devolucao", motivo: "" });
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Orçamento (ID)">
          <Input type="number" placeholder="opcional" value={form.orc} onChange={(e) => setForm({ ...form, orc: e.target.value })} className="w-28" />
        </Field>
        <Field label="Produto (ID)">
          <Input type="number" value={form.var} onChange={(e) => setForm({ ...form, var: e.target.value })} className="w-28" />
        </Field>
        <Field label="Quantidade">
          <Input type="number" step="any" value={form.qtd} onChange={(e) => setForm({ ...form, qtd: e.target.value })} className="w-24" />
        </Field>
        <Field label="Tipo">
          <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} className="w-40">
            <option value="devolucao">Devolução</option>
            <option value="troca">Troca</option>
          </Select>
        </Field>
        <Field label="Motivo">
          <Input value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} className="w-48" />
        </Field>
        <Button variant="primary" onClick={() => void registrar()}>
          Registrar devolução
        </Button>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhuma devolução.
        </div>
      ) : (
        <Table>
          <THead cols={["Produto", "Qtd", "Tipo", "Motivo", "Status", "Data"]} />
          <TBody>
            {rows.map((d) => (
              <tr key={d.id} className="hover:bg-gray-50">
                <Cell>
                  <span className="font-medium">{d.produto_nome}</span>
                  {d.sku ? <div className="font-mono text-xs text-gray-400">{d.sku}</div> : null}
                </Cell>
                <Cell>{d.quantidade}</Cell>
                <Cell>
                  <Badge tone="gray">{d.tipo}</Badge>
                </Cell>
                <Cell>{d.motivo || "—"}</Cell>
                <Cell>
                  <Badge tone={d.status === "estornada" ? "green" : "gray"}>{d.status}</Badge>
                </Cell>
                <Cell className="text-xs text-gray-500">{fmtDate(d.criado_em)}</Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}