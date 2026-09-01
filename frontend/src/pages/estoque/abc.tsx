// pages/estoque/abc.tsx — ABC histórica (COM-001): calcular por período/critério, versionar, aplicar.
import { useEffect, useState } from "react";
import { api, type AbcCalculo, type AbcItem } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Field, Input, Loading, Select } from "../../ui/ui";

export function AbcHistorica() {
  const [versoes, setVersoes] = useState<{ id: number; criterio: string; data_inicio: string; data_fim: string; origem: string; total: number; itens: number; criado_em: string }[] | null>(null);
  const [detalhe, setDetalhe] = useState<AbcCalculo | null>(null);
  const [form, setForm] = useState({ criterio: "consumo", data_inicio: "", data_fim: "" });
  const [rodando, setRodando] = useState(false);

  const carregar = async () => {
    setVersoes(null);
    try {
      setVersoes((await api.listarAbcHistorica()).calculos);
    } catch (e) {
      toast("Erro ao carregar ABC: " + (e as Error).message, "error");
      setVersoes([]);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const calcular = async () => {
    if (!form.data_inicio || !form.data_fim) {
      toast("Informe o período", "error");
      return;
    }
    setRodando(true);
    try {
      const r = await api.calcularAbcHistorica(form);
      toast(`ABC calculada: ${r.calculo.total_itens} itens`, "success");
      setDetalhe(r.calculo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setRodando(false);
    }
  };

  const aplicar = async () => {
    if (!detalhe) return;
    try {
      const r = await api.aplicarAbcHistorica(detalhe.id);
      toast(`Aplicado em ${r.resultado.aplicados} produto(s) (${r.resultado.criterio}, ${r.resultado.periodo})`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const abrir = async (id: number) => {
    try {
      setDetalhe((await api.detalheAbcHistorica(id)).calculo as AbcCalculo);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-gray-200 bg-white p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Calcular ABC histórica (vendas finalizadas, sem cancelamentos)</div>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Critério">
            <Select value={form.criterio} onChange={(e) => setForm({ ...form, criterio: e.target.value })} className="w-40">
              <option value="quantidade">Quantidade</option>
              <option value="consumo">Consumo</option>
              <option value="receita">Receita</option>
              <option value="margem">Margem</option>
              <option value="frequencia">Frequência</option>
            </Select>
          </Field>
          <Field label="Início">
            <Input type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} />
          </Field>
          <Field label="Fim">
            <Input type="date" value={form.data_fim} onChange={(e) => setForm({ ...form, data_fim: e.target.value })} />
          </Field>
          <Button variant="primary" onClick={() => void calcular()} disabled={rodando}>
            {rodando ? "Calculando…" : "Calcular"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-gray-200 bg-white p-3">
          <div className="mb-2 text-xs font-semibold text-gray-500">Versões</div>
          {versoes === null ? (
            <Loading />
          ) : versoes.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-400">Nenhuma versão calculada.</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {versoes.map((v) => (
                <button key={v.id} className="flex w-full items-center justify-between py-2 text-sm hover:bg-gray-50" onClick={() => void abrir(v.id)}>
                  <span className="text-blue-700 hover:underline">{v.criterio}</span>
                  <span className="text-xs text-gray-500">
                    {fmtDate(v.data_inicio)} → {fmtDate(v.data_fim)} · {v.itens} itens · {fmtMoney(v.total)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {detalhe && (
          <div className="rounded-md border border-gray-200 bg-white p-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs font-semibold text-gray-500">
                Resultado · {detalhe.criterio} · {fmtDate(detalhe.data_inicio)} → {fmtDate(detalhe.data_fim)}
              </div>
              <Button size="sm" variant="primary" onClick={() => void aplicar()}>Aplicar nos produtos</Button>
            </div>
            <div className="mb-2 flex flex-wrap gap-2 text-xs text-gray-600">
              {["A", "B", "C"].map((c) => (
                <span key={c} className="rounded bg-gray-100 px-2 py-1">
                  {c}: {detalhe.resumo[c]?.produtos ?? 0} ({detalhe.resumo[c]?.pct ?? 0}%)
                </span>
              ))}
            </div>
            <div className="max-h-64 divide-y divide-gray-100 overflow-y-auto">
              {detalhe.itens.slice(0, 50).map((i: AbcItem) => (
                <div key={i.produto_id} className="flex items-center justify-between py-1 text-sm">
                  <span className="flex items-center gap-2">
                    <Badge tone={i.classe === "A" ? "green" : i.classe === "B" ? "amber" : "gray"}>{i.classe}</Badge>
                    <span className="truncate">{i.produto_nome ?? `#${i.produto_id}`}</span>
                  </span>
                  <span className="text-xs text-gray-500">{i.valor.toLocaleString("pt-BR")}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}