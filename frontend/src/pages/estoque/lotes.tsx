// pages/estoque/lotes.tsx - módulo Estoque (Lotes) — rastreabilidade (EST-008).

import { useEffect, useState } from "react";
import { api, type Deposito, type LoteItem, type LotePayload, type RecallItem } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, Select, Table, TBody, THead } from "../../ui/ui";

function statusLote(l: LoteItem): string {
  if (l.data_validade && l.data_validade.slice(0, 10) <= new Date().toISOString().slice(0, 10)) return "vencido";
  return l.status === "bloqueado" ? "bloqueado" : "ativo";
}

export function Lotes({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<LoteItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [recall, setRecall] = useState<RecallItem[] | null>(null);
  const [recallProduto, setRecallProduto] = useState("");
  const [form, setForm] = useState({ deposito_id: "", produto_id: "", codigo: "", quantidade: "", fabricacao: "", validade: "", origem: "avulsa", documento: "", custo_unitario: "", observacao: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarLotes());
    } catch {
      toast("Erro ao carregar lotes", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    const payload: LotePayload = {
      deposito_id: Number(form.deposito_id),
      produto_id: Number(form.produto_id),
      codigo: form.codigo.trim(),
      quantidade: parseFloat(form.quantidade.replace(",", ".")),
      data_fabricacao: form.fabricacao || undefined,
      data_validade: form.validade || undefined,
      origem: form.origem,
      documento: form.documento.trim() || undefined,
      custo_unitario: form.custo_unitario.trim() !== "" ? parseFloat(form.custo_unitario.replace(",", ".")) : undefined,
      observacao: form.observacao.trim() || undefined,
    };
    if (!payload.deposito_id || !payload.produto_id || !payload.codigo) {
      toast("Preencha depósito, produto e código do lote", "error");
      return;
    }
    try {
      await api.criarLote(payload);
      setModalOpen(false);
      toast("Lote criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternarStatus = async (l: LoteItem) => {
    const novo = l.status === "bloqueado" ? "ativo" : "bloqueado";
    try {
      await api.alterarStatusLote(l.id, novo);
      toast(`Lote ${novo === "bloqueado" ? "bloqueado" : "reaberto"}`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const verRecall = async (l: LoteItem) => {
    try {
      setRecall((await api.recallLote(l.produto_id, l.id)).itens);
      setRecallProduto(`${l.codigo} — ${l.produto_nome}`);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo lote
        </Button>
        {recall !== null && (
          <span className="text-xs text-gray-500">
            Recall {recallProduto}: {recall.length} venda(s) afetada(s){" "}
            <button className="text-blue-600 hover:underline" onClick={() => setRecall(null)}>fechar</button>
          </span>
        )}
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "Lote", "Depósito", "Qtd", "Origem", "Custo", "Validade", "Status", "Ações"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={9} message="Nenhum lote" />
            ) : (
              rows.map((l) => {
                const st = statusLote(l);
                return (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <Cell>
                      <span className="font-medium">{l.produto_nome}</span>
                      <div className="text-xs text-gray-400">{l.sku}</div>
                    </Cell>
                    <Cell className="font-mono text-xs">{l.codigo}</Cell>
                    <Cell>{l.deposito_nome}</Cell>
                    <Cell className="font-medium">{l.quantidade}</Cell>
                    <Cell className="text-xs text-gray-500">{l.origem ?? "avulsa"}</Cell>
                    <Cell className="text-xs text-gray-500">{l.custo_unitario ? fmtMoney(l.custo_unitario) : "—"}</Cell>
                    <Cell className="text-xs text-gray-500">{l.data_validade ? fmtDate(l.data_validade) : "—"}</Cell>
                    <Cell>
                      <Badge tone={st === "ativo" ? "green" : st === "vencido" ? "red" : "amber"}>{st}</Badge>
                    </Cell>
                    <Cell className="flex gap-2">
                      <Button size="sm" variant="ghost" onClick={() => void alternarStatus(l)}>
                        {l.status === "bloqueado" ? "Reabrir" : "Bloquear"}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => void verRecall(l)}>
                        Recall
                      </Button>
                    </Cell>
                  </tr>
                );
              })
            )}
          </TBody>
        </Table>
      )}

      {recall !== null && (
        <div className="mt-3 rounded-md border border-gray-200 bg-white p-3">
          <div className="divide-y divide-gray-100">
            {recall.length === 0 && <p className="py-2 text-sm text-gray-400">Nenhuma venda vinculada a este lote.</p>}
            {recall.map((r, i) => (
              <div key={i} className="flex flex-wrap items-center justify-between py-1 text-sm">
                <span>
                  <span className="font-medium">{r.cliente}</span>
                  <span className="ml-2 text-xs text-gray-500">{r.cliente_doc}</span>
                </span>
                <span className="text-xs text-gray-500">
                  {r.orcamento_numero} · qtd {r.quantidade} · {fmtDate(r.data)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo lote"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Depósito">
            <Select value={form.deposito_id} onChange={(e) => setForm({ ...form, deposito_id: e.target.value })}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Produto (ID)">
            <Input type="number" min={1} value={form.produto_id} onChange={(e) => setForm({ ...form, produto_id: e.target.value })} />
          </Field>
          <Field label="Código do lote">
            <Input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} />
          </Field>
          <Field label="Quantidade">
            <Input type="number" min={0} step="any" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Fabricação">
              <Input type="date" value={form.fabricacao} onChange={(e) => setForm({ ...form, fabricacao: e.target.value })} />
            </Field>
            <Field label="Validade">
              <Input type="date" value={form.validade} onChange={(e) => setForm({ ...form, validade: e.target.value })} />
            </Field>
            <Field label="Origem">
              <Select value={form.origem} onChange={(e) => setForm({ ...form, origem: e.target.value })}>
                <option value="avulsa">Avulsa</option>
                <option value="compra">Compra</option>
                <option value="producao">Produção</option>
              </Select>
            </Field>
            <Field label="Custo unitário">
              <Input inputMode="decimal" value={form.custo_unitario} onChange={(e) => setForm({ ...form, custo_unitario: e.target.value })} />
            </Field>
            <Field label="Documento (NF)">
              <Input value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} />
            </Field>
            <Field label="Observação">
              <Input value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  );
}


