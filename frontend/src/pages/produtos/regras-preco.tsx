// pages/produtos/regras-preco.tsx — regras de preço por contexto/prioridade (MDM-007).
import { useEffect, useState } from "react";
import { api, type PrecoRegra } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Loading, Select } from "../../ui/ui";

const CANAIS = ["varejo", "atacado", "contrato", "promocional"];

export function RegrasPreco({ produtoId }: { produtoId: number }) {
  const [rows, setRows] = useState<PrecoRegra[] | null>(null);
  const [prioridade, setPrioridade] = useState("10");
  const [canal, setCanal] = useState("varejo");
  const [clienteId, setClienteId] = useState("");
  const [segmento, setSegmento] = useState("");
  const [qtdMin, setQtdMin] = useState("");
  const [preco, setPreco] = useState("");
  const [desconto, setDesconto] = useState("");
  const [margemMin, setMargemMin] = useState("");
  const [salvando, setSalvando] = useState(false);

  const carregar = async () => {
    setRows(null);
    try {
      setRows((await api.listarRegrasPreco(produtoId)).regras);
    } catch (e) {
      toast("Erro ao carregar regras: " + (e as Error).message, "error");
      setRows([]);
    }
  };

  useEffect(() => {
    void carregar();
  }, [produtoId]);

  const salvar = async () => {
    const temPreco = preco.trim() !== "";
    const temDesconto = desconto.trim() !== "";
    if (!temPreco && !temDesconto) {
      toast("Informe preço ou desconto", "error");
      return;
    }
    const payload: Record<string, unknown> = {
      prioridade: Number(prioridade) || 10,
      canal: canal === "geral" ? null : canal,
      cliente_id: clienteId.trim() ? Number(clienteId) : null,
      segmento: segmento.trim() || null,
      quantidade_min: qtdMin.trim() ? Number(qtdMin) : null,
      preco: temPreco ? Number(preco.replace(",", ".")) : null,
      desconto_pct: temDesconto ? Number(desconto.replace(",", ".")) : null,
      margem_minima_pct: margemMin.trim() ? Number(margemMin.replace(",", ".")) : null,
    };
    setSalvando(true);
    try {
      await api.salvarRegraPreco(produtoId, payload as never);
      toast("Regra salva", "success");
      setPreco("");
      setDesconto("");
      setMargemMin("");
      setClienteId("");
      setSegmento("");
      setQtdMin("");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (id: number) => {
    try {
      await api.excluirRegraPreco(produtoId, id);
      toast("Regra removida", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  if (rows === null) return <Loading message="Carregando regras de preço…" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Regras de preço por contexto (canal, cliente, segmento, quantidade mínima) com prioridade e vigência.
        Prioridade menor vence; sem regra que casa, o motor usa tabela → motor → preço base. A margem mínima da
        regra alimenta a alçada (preço abaixo exige aprovação).
      </p>

      {rows.length === 0 ? (
        <p className="rounded-md border border-dashed border-gray-300 bg-white py-6 text-center text-sm text-gray-400">
          Nenhuma regra de preço configurada.
        </p>
      ) : (
        <div className="space-y-2">
          {rows.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
              <span>
                <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-500">prio {r.prioridade}</span>
                <span className="ml-2 font-medium">
                  {r.preco != null ? `R$ ${r.preco}` : `${r.desconto_pct}% off`}
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  {r.canal ? `canal ${r.canal}` : "geral"}
                  {r.cliente_id ? ` · cliente ${r.cliente_id}` : ""}
                  {r.segmento ? ` · ${r.segmento}` : ""}
                  {r.quantidade_min != null ? ` · qtd ≥ ${r.quantidade_min}` : ""}
                </span>
                {r.margem_minima_pct != null ? (
                  <span className="ml-2 text-xs text-amber-600">margem mín {r.margem_minima_pct}%</span>
                ) : null}
              </span>
              <Button size="sm" variant="ghost" onClick={() => void excluir(r.id)}>
                ×
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-md border border-dashed border-gray-300 p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Nova regra</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="Prioridade">
            <Input type="number" min={1} value={prioridade} onChange={(e) => setPrioridade(e.target.value)} />
          </Field>
          <Field label="Canal">
            <Select value={canal} onChange={(e) => setCanal(e.target.value)}>
              <option value="geral">Geral</option>
              {CANAIS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Cliente (ID)">
            <Input type="number" min={1} value={clienteId} onChange={(e) => setClienteId(e.target.value)} placeholder="—" />
          </Field>
          <Field label="Segmento">
            <Input value={segmento} onChange={(e) => setSegmento(e.target.value)} placeholder="ex.: construtora" />
          </Field>
          <Field label="Qtd mínima">
            <Input type="number" min={1} value={qtdMin} onChange={(e) => setQtdMin(e.target.value)} placeholder="—" />
          </Field>
          <Field label="Preço (R$)">
            <Input inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} placeholder="fixo" />
          </Field>
          <Field label="Desconto (%)">
            <Input inputMode="decimal" value={desconto} onChange={(e) => setDesconto(e.target.value)} placeholder="—" />
          </Field>
          <Field label="Margem mínima (%)">
            <Input inputMode="decimal" value={margemMin} onChange={(e) => setMargemMin(e.target.value)} placeholder="—" />
          </Field>
        </div>
        <div className="mt-3">
          <Button size="sm" variant="primary" onClick={() => void salvar()} disabled={salvando}>
            {salvando ? "Salvando…" : "+ Salvar regra"}
          </Button>
        </div>
      </div>
    </div>
  );
}