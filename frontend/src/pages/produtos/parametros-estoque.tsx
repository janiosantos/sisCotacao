// pages/produtos/parametros-estoque.tsx — parâmetros de planejamento por depósito (EST-005).
import { useEffect, useState } from "react";
import { api, type EstoqueParametro } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Loading, Select } from "../../ui/ui";

export function ParametrosEstoque({ produtoId }: { produtoId: number }) {
  const [rows, setRows] = useState<EstoqueParametro[] | null>(null);
  const [depositos, setDepositos] = useState<{ id: number; nome: string }[]>([]);
  const [dep, setDep] = useState("");
  const [min, setMin] = useState("");
  const [max, setMax] = useState("");
  const [ponto, setPonto] = useState("");
  const [seguranca, setSeguranca] = useState("");
  const [lead, setLead] = useState("");
  const [loteMin, setLoteMin] = useState("");
  const [loteMax, setLoteMax] = useState("");
  const [loteMult, setLoteMult] = useState("");
  const [politica, setPolitica] = useState("manual");
  const [fonte, setFonte] = useState("manual");
  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);

  const carregar = async () => {
    setRows(null);
    try {
      const [p, d] = await Promise.all([api.listarParametrosEstoque(produtoId), api.listarDepositos()]);
      setRows(p.parametros);
      setDepositos(d);
      if (d.length && !dep) setDep(String(d[0].id));
    } catch (e) {
      toast("Erro ao carregar parâmetros: " + (e as Error).message, "error");
      setRows([]);
    }
  };

  useEffect(() => {
    void carregar();
  }, [produtoId]);

  const n = (v: string) => (v.trim() !== "" ? Number(v.replace(",", ".")) : null);

  const salvar = async () => {
    if (!dep) {
      toast("Selecione o depósito", "error");
      return;
    }
    setSalvando(true);
    try {
      await api.salvarParametroEstoque({
        produto_id: produtoId,
        deposito_id: Number(dep),
        politica,
        minimo: n(min),
        maximo: n(max),
        ponto_pedido: n(ponto),
        estoque_seguranca: n(seguranca),
        lead_time_dias: n(lead) ? Math.round(n(lead)!) : null,
        lote_minimo: n(loteMin),
        lote_maximo: n(loteMax),
        lote_multiplo: n(loteMult),
        fonte_valor: fonte,
        motivo: motivo.trim() || null,
      });
      toast("Parâmetro salvo", "success");
      setMin(""); setMax(""); setPonto(""); setSeguranca(""); setLead(""); setLoteMin(""); setLoteMax(""); setLoteMult(""); setMotivo("");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (depositoId: number) => {
    try {
      await api.excluirParametroEstoque(produtoId, depositoId);
      toast("Parâmetro removido", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  if (rows === null) return <Loading message="Carregando parâmetros…" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Parâmetros de planejamento por depósito (EST-005): política, mínimo/máximo, ponto de pedido, estoque de
        segurança, lead time e lote. Alimentam o motor de reposição (COM-004). Fallback para os limites legados quando
        não configurado.
      </p>

      {rows.length === 0 ? (
        <p className="rounded-md border border-dashed border-gray-300 bg-white py-6 text-center text-sm text-gray-400">
          Nenhum parâmetro configurado.
        </p>
      ) : (
        <div className="space-y-2">
          {rows.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
              <span>
                <span className="font-medium">Depósito {p.deposito_id}</span>
                <span className="ml-2 text-xs text-gray-500">
                  {p.minimo != null ? `mín ${p.minimo}` : "—"} · {p.maximo != null ? `máx ${p.maximo}` : "—"} ·{" "}
                  {p.ponto_pedido != null ? `ponto ${p.ponto_pedido}` : "—"} ·{" "}
                  {p.estoque_seguranca != null ? `seg ${p.estoque_seguranca}` : "—"}
                  {p.lead_time_dias ? ` · lead ${p.lead_time_dias}d` : ""}
                  {p.lote_multiplo ? ` · lote ×${p.lote_multiplo}` : ""}
                </span>
                <span className="ml-2 text-xs text-gray-400">
                  {p.politica} · {p.fonte_valor}
                </span>
              </span>
              <Button size="sm" variant="ghost" onClick={() => void excluir(p.deposito_id)}>
                ×
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-md border border-dashed border-gray-300 p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Novo parâmetro</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="Depósito">
            <Select value={dep} onChange={(e) => setDep(e.target.value)}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Política">
            <Select value={politica} onChange={(e) => setPolitica(e.target.value)}>
              <option value="manual">Manual</option>
              <option value="calculada">Calculada</option>
            </Select>
          </Field>
          <Field label="Fonte do valor">
            <Select value={fonte} onChange={(e) => setFonte(e.target.value)}>
              <option value="manual">Manual</option>
              <option value="abc">ABC</option>
              <option value="lead_time_real">Lead time real</option>
              <option value="custom">Custom</option>
            </Select>
          </Field>
          <Field label="Mínimo">
            <Input inputMode="decimal" value={min} onChange={(e) => setMin(e.target.value)} />
          </Field>
          <Field label="Máximo">
            <Input inputMode="decimal" value={max} onChange={(e) => setMax(e.target.value)} />
          </Field>
          <Field label="Ponto de pedido">
            <Input inputMode="decimal" value={ponto} onChange={(e) => setPonto(e.target.value)} />
          </Field>
          <Field label="Estoque de segurança">
            <Input inputMode="decimal" value={seguranca} onChange={(e) => setSeguranca(e.target.value)} />
          </Field>
          <Field label="Lead time (dias)">
            <Input type="number" min={0} value={lead} onChange={(e) => setLead(e.target.value)} />
          </Field>
          <Field label="Lote mínimo">
            <Input inputMode="decimal" value={loteMin} onChange={(e) => setLoteMin(e.target.value)} />
          </Field>
          <Field label="Lote máximo">
            <Input inputMode="decimal" value={loteMax} onChange={(e) => setLoteMax(e.target.value)} />
          </Field>
          <Field label="Lote múltiplo">
            <Input inputMode="decimal" value={loteMult} onChange={(e) => setLoteMult(e.target.value)} />
          </Field>
          <Field label="Motivo">
            <Input value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </Field>
        </div>
        <div className="mt-3">
          <Button size="sm" variant="primary" onClick={() => void salvar()} disabled={salvando}>
            {salvando ? "Salvando…" : "+ Salvar parâmetro"}
          </Button>
        </div>
      </div>
    </div>
  );
}