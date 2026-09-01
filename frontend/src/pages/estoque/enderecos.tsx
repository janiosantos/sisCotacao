// pages/estoque/enderecos.tsx — endereçamento (EST-007): posições, saldo por posição e movimentação logada.
import { useEffect, useState } from "react";
import { api, type EnderecoPosicao } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Select, Table, TBody, THead } from "../../ui/ui";

export function Enderecos({ depositos }: { depositos: { id: number; nome: string }[] }) {
  const [rows, setRows] = useState<EnderecoPosicao[]>([]);
  const [dep, setDep] = useState(depositos[0] ? String(depositos[0].id) : "");
  const [q, setQ] = useState("");
  const [codigo, setCodigo] = useState("");
  const [itensPos, setItensPos] = useState<number | null>(null);
  const [itens, setItens] = useState<{ produto_id: number; sku: string; produto_nome: string; quantidade: number; primaria: boolean }[]>([]);
  const [mv, setMv] = useState({ produto: "", quantidade: "", de: "", para: "" });

  const buscar = async () => {
    try {
      setRows((await api.listarEnderecos({ deposito_id: dep ? Number(dep) : undefined, q: q || undefined })).posicoes);
    } catch (e) {
      toast("Erro ao carregar posições: " + (e as Error).message, "error");
    }
  };

  useEffect(() => {
    void buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);

  const criar = async () => {
    if (!dep || !codigo.trim()) {
      toast("Depósito e código são obrigatórios", "error");
      return;
    }
    try {
      await api.criarEndereco({ deposito_id: Number(dep), codigo: codigo.trim() });
      toast("Posição criada", "success");
      setCodigo("");
      await buscar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const verEstoque = async (id: number) => {
    try {
      setItens((await api.estoqueEndereco(id)).itens);
      setItensPos(id);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const excluir = async (id: number) => {
    try {
      await api.excluirEndereco(id);
      toast("Posição desativada", "success");
      await buscar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const movimentar = async () => {
    if (!mv.produto || !mv.quantidade || (!mv.de && !mv.para)) {
      toast("Produto, quantidade e ao menos uma posição", "error");
      return;
    }
    try {
      await api.movimentarEndereco({
        produto_id: Number(mv.produto),
        quantidade: Number(mv.quantidade),
        de_posicao_id: mv.de ? Number(mv.de) : null,
        para_posicao_id: mv.para ? Number(mv.para) : null,
      });
      toast("Movimentado", "success");
      setMv({ produto: "", quantidade: "", de: "", para: "" });
      await buscar();
      if (itensPos) await verEstoque(itensPos);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-48">
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>{d.nome}</option>
            ))}
          </Select>
        </Field>
        <Field label="Buscar posição">
          <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void buscar(); }} placeholder="código…" />
        </Field>
        <Field label="Nova posição">
          <Input value={codigo} onChange={(e) => setCodigo(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void criar(); }} placeholder="RUA-MÓD-POS-NÍVEL" />
        </Field>
        <Button variant="primary" onClick={() => void criar()}>+ Criar posição</Button>
      </div>

      <div className="rounded-md border border-gray-200 bg-white p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Movimentar entre posições</div>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Produto (ID)">
            <Input className="w-20" inputMode="numeric" value={mv.produto} onChange={(e) => setMv((s) => ({ ...s, produto: e.target.value }))} />
          </Field>
          <Field label="Quantidade">
            <Input className="w-20" inputMode="decimal" value={mv.quantidade} onChange={(e) => setMv((s) => ({ ...s, quantidade: e.target.value }))} />
          </Field>
          <Field label="De (posição ID, vazio = entrada)">
            <Input className="w-24" inputMode="numeric" value={mv.de} onChange={(e) => setMv((s) => ({ ...s, de: e.target.value }))} />
          </Field>
          <Field label="Para (posição ID, vazio = saída)">
            <Input className="w-24" inputMode="numeric" value={mv.para} onChange={(e) => setMv((s) => ({ ...s, para: e.target.value }))} />
          </Field>
          <Button variant="secondary" onClick={() => void movimentar()}>Mover</Button>
        </div>
      </div>

      <Table>
        <THead cols={["Código", "Depósito", "Itens", "Status", "Ações"]} />
        <TBody>
          {rows.length === 0 && <EmptyRow colSpan={5} message="Nenhuma posição" />}
          {rows.map((p) => (
            <tr key={p.id}>
              <Cell className="font-medium">{p.codigo}</Cell>
              <Cell>{p.deposito_nome}</Cell>
              <Cell>{p.posicoes_ocupadas}</Cell>
              <Cell><Badge tone="green">Ativa</Badge></Cell>
              <Cell className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => void verEstoque(p.id)}>Estoque</Button>
                <Button size="sm" variant="ghost" onClick={() => void excluir(p.id)}>×</Button>
              </Cell>
            </tr>
          ))}
        </TBody>
      </Table>

      {itensPos !== null && (
        <div className="rounded-md border border-gray-200 bg-white p-3">
          <div className="mb-2 text-xs font-semibold text-gray-500">Estoque na posição #{itensPos}</div>
          <div className="divide-y divide-gray-100">
            {itens.length === 0 && <p className="py-2 text-sm text-gray-400">Posição vazia.</p>}
            {itens.map((i) => (
              <div key={i.produto_id} className="flex items-center justify-between py-1 text-sm">
                <span>{i.sku} — {i.produto_nome} {i.primaria && <Badge tone="blue">primária</Badge>}</span>
                <span className="font-medium">{i.quantidade}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}