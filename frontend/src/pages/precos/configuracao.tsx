import { useEffect, useState } from "react";
import { api, type ConfiguracaoPrecificacao } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Card, Field, Input, Select } from "../../ui/ui";

type Form = Omit<ConfiguracaoPrecificacao, "id" | "impostos_atual_pct" | "reforma_tributaria_pct" | "despesa_fixa_real_pct" | "despesa_variavel_real_pct" | "referencia_atividade">;

const MONEY_FIELDS: { key: keyof Form; label: string }[] = [
  { key: "faturamento_mensal", label: "Faturamento bruto mensal" },
  { key: "despesa_fixa_mensal", label: "Despesas fixas mensais" },
  { key: "despesa_variavel_mensal", label: "Despesas variáveis mensais" },
];

const TAX_FIELDS: { key: keyof Form; label: string }[] = [
  { key: "imposto_simples_pct", label: "Simples Nacional" },
  { key: "imposto_icms_pct", label: "ICMS" },
  { key: "imposto_pis_pct", label: "PIS" },
  { key: "imposto_cofins_pct", label: "COFINS" },
  { key: "imposto_ir_pct", label: "IR" },
  { key: "imposto_csll_pct", label: "CSLL" },
];

function toForm(config: ConfiguracaoPrecificacao): Form {
  const form = { ...config } as unknown as Form;
  return form;
}

export function ConfiguracaoPrecificacao() {
  const [form, setForm] = useState<Form | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    void api.configuracaoPrecificacao().then((config) => setForm(toForm(config))).catch(() => toast("Não foi possível carregar as premissas", "error"));
  }, []);

  const set = (key: keyof Form, value: string | boolean) => {
    setForm((old) => old ? { ...old, [key]: typeof value === "boolean" ? value : Number(value.replace(",", ".")) || 0 } : old);
  };

  const salvar = async () => {
    if (!form) return;
    setSalvando(true);
    try {
      const saved = await api.salvarConfiguracaoPrecificacao(form);
      setForm(toForm(saved));
      toast("Premissas de precificação salvas", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  if (!form) return <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">Carregando premissas…</div>;
  const atividade = form.atividade === "comercio" ? "Comércio" : form.atividade === "servicos" ? "Serviços" : "Indústria";

  return (
    <div className="space-y-4">
      <Card className="border-brand-200 bg-brand-50/40 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2"><Badge tone="blue">Base do cálculo</Badge><h2 className="text-base font-semibold text-slate-900">Premissas do negócio</h2></div>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">Informe os números reais do mês. Eles alimentam a despesa fixa, os tributos e a taxa média do cartão usados na formação de preço. A planilha de referência usa essas premissas para evitar decisões baseadas apenas no custo de compra.</p>
          </div>
          <Button variant="primary" onClick={() => void salvar()} disabled={salvando}>{salvando ? "Salvando…" : "Salvar premissas"}</Button>
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <h3 className="font-semibold text-slate-900">1. Faturamento e despesas</h3>
          <p className="mb-4 mt-1 text-xs leading-5 text-slate-500">A despesa fixa real é calculada como despesas fixas ÷ faturamento. Se a referência de atividade estiver ligada, ela será usada no lugar desse percentual.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {MONEY_FIELDS.map((field) => <Field key={field.key} label={`${field.label} (R$)`}><Input type="number" min="0" step="0.01" value={String(form[field.key] ?? 0)} onChange={(e) => set(field.key, e.target.value)} /></Field>)}
            <Field label="Atividade de referência"><Select value={form.atividade} onChange={(e) => setForm({ ...form, atividade: e.target.value as Form["atividade"] })}><option value="comercio">Comércio</option><option value="servicos">Serviços</option><option value="industria">Indústria</option></Select></Field>
            <Field label="Taxa média de cartão (%)"><Input type="number" min="0" max="100" step="0.01" value={String(form.taxa_cartao_pct)} onChange={(e) => set("taxa_cartao_pct", e.target.value)} /></Field>
          </div>
          <label className="mt-4 flex cursor-pointer items-start gap-2 text-sm text-slate-700"><input type="checkbox" checked={form.usar_referencia_atividade} onChange={(e) => set("usar_referencia_atividade", e.target.checked)} className="mt-0.5 accent-brand-600" /><span><strong>Usar referência de despesa fixa da atividade</strong><span className="block text-xs text-slate-500">Para Comércio, a planilha sugere até 25%. Desligue para usar o percentual real ou a competência aprovada.</span></span></label>
          <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 sm:grid-cols-2">
            <Field label="Competência aprovada para preços"><Input type="month" value={form.competencia_precificacao || ""} onChange={(e) => setForm({ ...form, competencia_precificacao: e.target.value || null })} /></Field>
            <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-700"><input type="checkbox" checked={form.usar_competencia_aprovada} onChange={(e) => set("usar_competencia_aprovada", e.target.checked)} className="accent-brand-600" /> Usar competência aprovada quando existir</label>
          </div>
          <label className="mt-3 flex cursor-pointer items-start gap-2 text-sm text-slate-700"><input type="checkbox" checked={form.incluir_despesas_variaveis_rateadas} onChange={(e) => set("incluir_despesas_variaveis_rateadas", e.target.checked)} className="mt-0.5 accent-brand-600" /><span><strong>Incluir despesas variáveis elegíveis no divisor</strong><span className="block text-xs text-slate-500">Inclui somente a apuração aprovada. Confira componentes como cartão, comissão e frete para evitar dupla contagem.</span></span></label>
        </Card>

        <Card className="p-5">
          <h3 className="font-semibold text-slate-900">2. Tributos considerados</h3>
          <p className="mb-4 mt-1 text-xs leading-5 text-slate-500">Use as alíquotas informadas pela contabilidade. O motor não substitui a apuração fiscal por produto e contexto.</p>
          <div className="grid gap-3 sm:grid-cols-2">{TAX_FIELDS.map((field) => <Field key={field.key} label={`${field.label} (%)`}><Input type="number" min="0" max="100" step="0.01" value={String(form[field.key] ?? 0)} onChange={(e) => set(field.key, e.target.value)} /></Field>)}</div>
          <div className="mt-4 border-t border-slate-100 pt-4"><p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Cenário Reforma Tributária</p><div className="grid gap-3 sm:grid-cols-3"><Field label="IBS (%)"><Input type="number" min="0" max="100" step="0.01" value={String(form.ibs_pct)} onChange={(e) => set("ibs_pct", e.target.value)} /></Field><Field label="CBS (%)"><Input type="number" min="0" max="100" step="0.01" value={String(form.cbs_pct)} onChange={(e) => set("cbs_pct", e.target.value)} /></Field><Field label="Cenário usado"><Select value={form.cenario_tributario} onChange={(e) => setForm({ ...form, cenario_tributario: e.target.value as Form["cenario_tributario"] })}><option value="atual">Tributos atuais</option><option value="reforma">IBS/CBS fora do divisor</option></Select></Field></div></div>
        </Card>
      </div>

      <Card className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold text-slate-900">Como estas premissas entram no preço</h3><p className="mt-1 text-sm text-slate-500">Atividade selecionada: {atividade}. A simulação mostra cada componente antes de permitir aplicar uma tabela.</p></div><div className="grid grid-cols-2 gap-3 text-right text-sm sm:grid-cols-4"><div><div className="text-xs text-slate-500">Impostos atuais</div><strong>{(TAX_FIELDS.reduce((sum, field) => sum + Number(form[field.key] || 0), 0)).toFixed(2)}%</strong></div><div><div className="text-xs text-slate-500">IBS + CBS</div><strong>{(Number(form.ibs_pct) + Number(form.cbs_pct)).toFixed(2)}%</strong></div><div><div className="text-xs text-slate-500">Fixa real</div><strong>{form.faturamento_mensal > 0 ? ((form.despesa_fixa_mensal / form.faturamento_mensal) * 100).toFixed(2) + "%" : "—"}</strong></div><div><div className="text-xs text-slate-500">Referência fixa</div><strong>{form.atividade === "comercio" ? "25%" : form.atividade === "servicos" ? "40%" : "30%"}</strong></div></div></div><p className="mt-4 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-800">Atenção: o rateio variável só entra quando ativado e existe competência aprovada. Componentes diretamente atribuídos ao produto, como comissão, cartão e frete percentual, não devem ser repetidos no rateio.</p></Card>
    </div>
  );
}
