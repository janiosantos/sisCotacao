// pages/precos/simulador.tsx - formação de preço pelo método divisor.

import { useState } from "react";
import { api, type CalculoPreco, type ProdutoResumo } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Card, Field, Input, Loading, Select, StatCard, Table, TBody } from "../../ui/ui";
import { ProductSearch } from "../../ui/product-search";

function pct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(2).replace(".", ",") + "%";
}

function optionalNumber(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function Simulador() {
  const [canal, setCanal] = useState("varejo");
  const [margem, setMargem] = useState("");
  const [comissao, setComissao] = useState("");
  const [embalagem, setEmbalagem] = useState("");
  const [frete, setFrete] = useState("");
  const [fretePct, setFretePct] = useState("");
  const [cartao, setCartao] = useState("");
  const [impostos, setImpostos] = useState("");
  const [usarReferencia, setUsarReferencia] = useState(true);
  const [cenario, setCenario] = useState<"atual" | "reforma">("atual");
  const [selecionada, setSelecionada] = useState<ProdutoResumo | null>(null);
  const [resultado, setResultado] = useState<CalculoPreco | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const calcular = async () => {
    if (!selecionada) {
      toast("Selecione um produto na busca", "error");
      return;
    }
    const params: Record<string, unknown> = { canal, usar_referencia_atividade: usarReferencia ? "true" : "false", cenario_tributario: cenario };
    const values: [string, string][] = [["margem", margem], ["comissao", comissao], ["embalagem_unitaria", embalagem], ["frete_unitario", frete], ["frete_pct", fretePct], ["cartao_pct", cartao], ["impostos_pct", impostos]];
    values.forEach(([key, value]) => {
      const parsed = optionalNumber(value);
      if (parsed !== undefined) params[key] = parsed;
    });
    setCarregando(true);
    setErro("");
    try {
      setResultado(await api.calcularPreco(selecionada.id, params));
    } catch (e) {
      setResultado(null);
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  const memoria = resultado?.metodologia_memoria;
  const f = resultado?.fiscal;
  const linha = (rotulo: string, valor: string, destaque = false) => (
    <tr key={rotulo} className={destaque ? "bg-brand-50" : undefined}>
      <td className={`px-4 py-2.5 text-sm ${destaque ? "font-semibold text-brand-800" : "text-slate-600"}`}>{rotulo}</td>
      <td className={`px-4 py-2.5 text-right text-sm ${destaque ? "font-bold text-brand-700" : "font-medium text-slate-800"}`}>{valor}</td>
    </tr>
  );

  return (
    <div className="space-y-4">
      <Card className="border-brand-200 bg-brand-50/40 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><div className="flex items-center gap-2"><Badge tone="blue">Simulação segura</Badge><h2 className="text-base font-semibold text-slate-900">Formação de preço</h2></div><p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">O preço é formado pelo custo final do item dividido pelo percentual que sobra depois de impostos, despesas, taxas e lucro. O cálculo oficial acontece no servidor; esta tela apenas organiza as premissas.</p></div>
          <div className="rounded-lg border border-brand-200 bg-white px-3 py-2 text-xs text-brand-800"><strong>Fórmula</strong><div className="mt-1 font-mono">Preço = custo ÷ divisor</div></div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="mb-4 flex items-center justify-between gap-3"><div><h3 className="font-semibold text-slate-900">1. Escolha o item e o cenário</h3><p className="mt-1 text-xs text-slate-500">Deixe margem vazia para usar a margem padrão da tabela selecionada.</p></div><Badge tone="gray">Sem gravação</Badge></div>
        <div className="grid gap-3 lg:grid-cols-[minmax(260px,2fr)_150px_190px]">
          <Field label="Produto, código ou marca">
            <ProductSearch
              selected={selecionada}
              onSelect={(produto) => {
                setSelecionada(produto);
                setResultado(null);
              }}
              onClear={() => {
                setSelecionada(null);
                setResultado(null);
              }}
            />
          </Field>
          <Field label="Canal"><Select value={canal} onChange={(e) => setCanal(e.target.value)}><option value="varejo">Varejo</option><option value="atacado">Atacado</option><option value="contrato">Contrato</option><option value="promocional">Promocional</option></Select></Field>
          <Field label="Cenário tributário"><Select value={cenario} onChange={(e) => setCenario(e.target.value as "atual" | "reforma")}><option value="atual">Tributos atuais</option><option value="reforma">IBS/CBS fora do divisor</option></Select></Field>
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="p-5"><h3 className="font-semibold text-slate-900">2. Custo final do item</h3><p className="mb-4 mt-1 text-xs leading-5 text-slate-500">O custo líquido vem do motor de custos. Informe aqui somente adicionais exclusivos deste item.</p><div className="grid gap-3 sm:grid-cols-2"><Field label="Embalagem por unidade (R$)"><Input type="number" min="0" step="0.01" value={embalagem} onChange={(e) => setEmbalagem(e.target.value)} /></Field><Field label="Frete por unidade (R$)"><Input type="number" min="0" step="0.01" value={frete} onChange={(e) => setFrete(e.target.value)} /></Field><Field label="Frete sobre a venda (%)"><Input type="number" min="0" max="100" step="0.01" value={fretePct} onChange={(e) => setFretePct(e.target.value)} /></Field><Field label="Comissão sobre a venda (%)"><Input type="number" min="0" max="100" step="0.01" value={comissao} onChange={(e) => setComissao(e.target.value)} /></Field></div></Card>
        <Card className="p-5"><h3 className="font-semibold text-slate-900">3. Percentuais da venda</h3><p className="mb-4 mt-1 text-xs leading-5 text-slate-500">Percentuais são aplicados sobre o preço de venda, não somados diretamente ao custo.</p><div className="grid gap-3 sm:grid-cols-2"><Field label="Taxa de cartão (%)"><Input type="number" min="0" max="100" step="0.01" value={cartao} onChange={(e) => setCartao(e.target.value)} placeholder="Usar configuração" /></Field><Field label="Impostos atuais (%)"><Input type="number" min="0" max="100" step="0.01" value={impostos} onChange={(e) => setImpostos(e.target.value)} placeholder="Usar configuração" /></Field><Field label="Margem desejada (%)"><Input type="number" min="0" max="100" step="0.1" value={margem} onChange={(e) => setMargem(e.target.value)} placeholder="Usar tabela" /></Field></div><label className="mt-4 flex cursor-pointer items-start gap-2 text-sm text-slate-700"><input type="checkbox" checked={usarReferencia} onChange={(e) => setUsarReferencia(e.target.checked)} className="mt-0.5 accent-brand-600" /><span><strong>Usar despesa fixa de referência da atividade</strong><span className="block text-xs text-slate-500">Desmarque para usar o percentual real configurado em Premissas.</span></span></label><div className="mt-4 flex justify-end"><Button variant="primary" onClick={() => void calcular()} disabled={carregando}>{carregando ? "Calculando…" : "Calcular preço"}</Button></div></Card>
      </div>

      {erro ? <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">Não foi possível calcular: {erro}</div> : null}
      {carregando ? <Loading message="Calculando custo, fiscal e divisor…" /> : null}

      {resultado && memoria ? <div className="space-y-4"><div className="grid grid-cols-1 gap-3 sm:grid-cols-3"><StatCard label="Custo de formação" value={fmtMoney(memoria.custo_formacao)} sub={`Aquisição ${fmtMoney(memoria.custo_aquisicao)} + adicionais`} /><StatCard label="Preço mínimo" value={memoria.preco_minimo != null ? fmtMoney(memoria.preco_minimo) : "—"} sub="Cobre os custos sem margem" tone="highlight" /><StatCard label={cenario === "reforma" ? "Preço final sugerido" : "Preço sugerido"} value={resultado.preco_sugerido != null ? fmtMoney(resultado.preco_sugerido) : "—"} sub={cenario === "reforma" ? `Inclui ${fmtMoney(memoria.tributos_valor)} de IBS/CBS` : "Com margem configurada"} tone="success" /></div><div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]"><Card className="p-5"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-semibold text-slate-900">Memória de cálculo</h3><p className="mt-1 text-xs text-slate-500">Metodologia: markup divisor · {resultado.configuracao?.atividade_nome || "atividade"} · fixa via {resultado.configuracao?.despesas_fixas_origem || "parâmetro"}</p></div><Badge tone={memoria.alertas.length ? "amber" : "green"}>{memoria.alertas.length ? "Revisar alertas" : "Cálculo válido"}</Badge></div><Table><TBody>{linha("Custo líquido de aquisição", fmtMoney(memoria.custo_aquisicao))}{linha("Embalagem + frete unitário", fmtMoney(memoria.custo_formacao - memoria.custo_aquisicao))}{linha("Percentuais sobre a venda", pct(memoria.percentuais.custos_percentuais))}{linha("Margem desejada", pct(memoria.percentuais.margem))}{linha("Divisor", memoria.divisor.toFixed(6))}{linha("Markup multiplicador", memoria.markup_multiplicador != null ? memoria.markup_multiplicador.toFixed(4) + "x" : "—")}{cenario === "reforma" ? linha("IBS + CBS fora do divisor", `${pct(memoria.percentuais.tributo_fora_divisor)} · ${fmtMoney(memoria.tributos_valor)}`) : null}{linha("Preço sem tributos adicionais", memoria.preco_sem_tributos != null ? fmtMoney(memoria.preco_sem_tributos) : "—")}{linha("Preço final sugerido", memoria.preco_com_tributos != null ? fmtMoney(memoria.preco_com_tributos) : "—", true)}{linha("Margem efetiva", pct(resultado.margem_efetiva_pct))}{linha("Markup efetivo", pct(resultado.markup_efetivo_pct))}</TBody></Table></Card><Card className="p-5"><h3 className="font-semibold text-slate-900">Leitura para decisão</h3><div className="mt-3 space-y-3 text-sm leading-6 text-slate-600"><p><strong className="text-slate-900">Preço mínimo:</strong> abaixo dele, cada venda tende a consumir margem para cobrir despesas.</p><p><strong className="text-slate-900">Divisor:</strong> quanto maior a soma de despesas, taxas e margem, menor o divisor e maior o preço necessário.</p><p><strong className="text-slate-900">Preço sugerido:</strong> referência calculada. Compare com mercado antes de publicar e use a tabela de preço para formalizar a decisão.</p></div>{memoria.alertas.length > 0 ? <div className="mt-4 space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800"><strong>Alertas</strong>{memoria.alertas.map((alerta) => <p key={alerta}>• {alerta}</p>)}</div> : null}</Card></div></div> : null}

      {f ? <details className="rounded-xl border border-slate-200 bg-white p-5"><summary className="cursor-pointer text-sm font-semibold text-slate-800">Ver contexto fiscal consumido pelo custo líquido</summary><div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4"><div><span className="text-xs text-slate-500">Regime</span><div className="font-medium">{f.regime}</div></div><div><span className="text-xs text-slate-500">NCM</span><div className="font-medium">{f.ncm || "—"}</div></div><div><span className="text-xs text-slate-500">ICMS</span><div className="font-medium">{pct(f.aliquota_icms)}</div></div><div><span className="text-xs text-slate-500">Créditos</span><div className="font-medium">{pct(f.creditos.total_pct)}</div></div></div></details> : null}
    </div>
  );
}
