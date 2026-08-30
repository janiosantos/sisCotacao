// pages/precos/simulador.tsx - módulo Preços (Simulador).

import { useEffect, useRef, useState } from "react";
import { api, type CalculoPreco, type ProdutoResumo } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Loading, Select, Table, TBody } from "../../ui/ui";

function pct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return n.toFixed(2).replace(".", ",") + "%";
}

export function Simulador() {
  const [busca, setBusca] = useState("");
  const [canal, setCanal] = useState("");
  const [margem, setMargem] = useState("");
  const [markup, setMarkup] = useState("");
  const [comissao, setComissao] = useState("");
  const [despesas, setDespesas] = useState("");
  const [taxas, setTaxas] = useState("");
  const [sugestoes, setSugestoes] = useState<ProdutoResumo[]>([]);
  const [selecionada, setSelecionada] = useState<ProdutoResumo | null>(null);
  const [resultado, setResultado] = useState<CalculoPreco | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!busca.trim()) {
      setSugestoes([]);
      return;
    }
    timer.current = setTimeout(() => {
      void api
        .listarProdutos({ q: busca.trim(), limit: 8, agrupado: 0 })
        .then((res) => {
          setSugestoes(res.items.filter((i): i is ProdutoResumo => "price" in i));
        })
        .catch(() => setSugestoes([]));
    }, 200);
    return () => clearTimeout(timer.current);
  }, [busca]);

  const calcular = async () => {
    if (!selecionada) {
      toast("Selecione um produto na busca", "error");
      return;
    }
    const num = (v: string) => (v === "" ? undefined : parseFloat(v.replace(",", ".")));
    const params: Record<string, unknown> = { canal: canal || undefined };
    const m = num(margem);
    const k = num(markup);
    const c = num(comissao);
    const d = num(despesas);
    const t = num(taxas);
    if (m !== undefined) params.margem = m;
    if (k !== undefined) params.markup = k;
    if (c !== undefined) params.comissao = c;
    if (d !== undefined) params.despesas = d;
    if (t !== undefined) params.taxas = t;

    setCarregando(true);
    setErro("");
    setResultado(null);
    try {
      setResultado(await api.calcularPreco(selecionada.id, params));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  const f = resultado?.fiscal;
  const linha = (rot: string, val: string) => (
    <tr>
      <td className="px-4 py-2 text-xs text-gray-500">{rot}</td>
      <td className="px-4 py-2 text-right font-medium">{val}</td>
    </tr>
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Produto" className="min-w-[280px]">
          <Input placeholder="Nome, SKU, marca…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </Field>
        <Field label="Canal">
          <Select value={canal} onChange={(e) => setCanal(e.target.value)} className="w-36">
            <option value="">—</option>
            <option value="varejo">Varejo</option>
            <option value="atacado">Atacado</option>
            <option value="contrato">Contrato</option>
            <option value="promocional">Promocional</option>
          </Select>
        </Field>
        <Field label="Margem %">
          <Input type="number" step="0.1" value={margem} onChange={(e) => setMargem(e.target.value)} className="w-24" />
        </Field>
        <Field label="Markup %">
          <Input type="number" step="0.1" value={markup} onChange={(e) => setMarkup(e.target.value)} className="w-24" />
        </Field>
        <Field label="Comissão %">
          <Input type="number" step="0.1" value={comissao} onChange={(e) => setComissao(e.target.value)} className="w-24" />
        </Field>
        <Field label="Despesas %">
          <Input type="number" step="0.1" value={despesas} onChange={(e) => setDespesas(e.target.value)} className="w-24" />
        </Field>
        <Field label="Taxas %">
          <Input type="number" step="0.1" value={taxas} onChange={(e) => setTaxas(e.target.value)} className="w-24" />
        </Field>
        <Button variant="primary" onClick={() => void calcular()}>
          Calcular
        </Button>
      </div>

      {sugestoes.length > 0 ? (
        <div className="mb-4 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {sugestoes.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setSelecionada(p);
                setSugestoes([]);
                setResultado(null);
              }}
              className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-gray-50"
            >
              <span>
                <span className="font-medium">{p.name}</span>
                {p.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{p.sku}</span> : null}
              </span>
              <span className="text-xs text-gray-500">
                {p.brand ? p.brand + " · " : ""}
                {fmtMoney(p.price)}
              </span>
            </button>
          ))}
        </div>
      ) : null}

      {selecionada ? (
        <p className="mb-4 text-sm text-gray-600">
          Selecionado: <span className="font-medium">{selecionada.name}</span>
          {selecionada.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{selecionada.sku}</span> : null} (produto #{selecionada.id})
        </p>
      ) : null}

      {carregando ? <Loading message="Calculando…" /> : null}
      {erro ? <div className="py-4 text-center text-sm text-gray-400">Erro: {erro}</div> : null}

      {resultado && selecionada ? (
        <div className="max-w-xl rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="mb-3 font-semibold text-gray-900">
            {selecionada.name}
            {selecionada.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{selecionada.sku}</span> : null}
          </h3>
          <Table>
            <TBody>
              {linha("Custo base", resultado.custo_base != null ? fmtMoney(resultado.custo_base) : "—")}
              {linha("Custo líquido", resultado.custo_liquido != null ? fmtMoney(resultado.custo_liquido) : "—")}
              {linha("Despesas + comissão + taxas", pct(resultado.despesas_pct.total))}
              {linha("Preço mínimo", resultado.preco_minimo != null ? fmtMoney(resultado.preco_minimo) : "—")}
              <tr className="bg-brand-50">
                <td className="px-4 py-2 text-sm font-semibold text-brand-700">Preço sugerido</td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-brand-700">
                  {resultado.preco_sugerido != null ? fmtMoney(resultado.preco_sugerido) : "—"}
                </td>
              </tr>
              {linha("Margem efetiva", pct(resultado.margem_efetiva_pct))}
              {linha("Markup efetivo", pct(resultado.markup_efetivo_pct))}
            </TBody>
          </Table>
          {resultado.observacao ? <p className="mt-2 text-xs text-gray-500">{resultado.observacao}</p> : null}

          {f ? (
            <details className="mt-3">
              <summary className="cursor-pointer text-sm font-medium text-gray-600">Detalhamento fiscal</summary>
              <div className="mt-2 grid grid-cols-2 gap-2 rounded-md bg-gray-50 p-3 text-sm">
                <div>
                  <span className="text-xs text-gray-400">Regime</span>
                  <div className="font-medium">{f.regime}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">NCM</span>
                  <div className="font-medium">{f.ncm || "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">CEST</span>
                  <div className="font-medium">{f.cest || "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">CSOSN</span>
                  <div className="font-medium">{f.csosn || "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">ICMS</span>
                  <div className="font-medium">{pct(f.aliquota_icms)}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">ICMS-ST</span>
                  <div className="font-medium">{f.icms_st.aplica ? pct(f.icms_st.aliquota) + " · MVA " + pct(f.icms_st.mva) : "não"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">DIFAL</span>
                  <div className="font-medium">{f.difal.aplica ? `${f.difal.uf_origem}→${f.difal.uf_dest || ""}` : "não"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">Créditos</span>
                  <div className="font-medium">{pct(f.creditos.total_pct)}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">Benefício</span>
                  <div className="font-medium">{f.beneficio ? f.beneficio.descricao : "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">IBPT (referência)</span>
                  <div className="font-medium">{f.ibpt ? pct(f.ibpt.federal + f.ibpt.estadual + f.ibpt.municipal) : "—"}</div>
                </div>
              </div>
            </details>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}


