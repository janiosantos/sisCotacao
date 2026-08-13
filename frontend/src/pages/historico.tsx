// pages/historico.tsx — histórico de preços (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type HistoricoPreco, type ProdutoComHistorico } from "../api/client";
import { fmtDate, fmtDateTime, fmtMoney } from "../ui/format";
import { Cell, Input, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";

const CORES = ["#C6871E", "#3C5468", "#35553B", "#A8432A", "#6B4A8F", "#1B7A8C", "#8F5F13", "#556B2F"];

export default function Historico() {
  const [codigos, setCodigos] = useState<ProdutoComHistorico[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [busca, setBusca] = useState("");
  const [produtoId, setProdutoId] = useState<number | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setCodigos(await api.produtosComHistorico());
      } catch {
        /* segue vazio */
      } finally {
        setCarregando(false);
      }
    })();
  }, []);

  const sugestoes = busca.trim()
    ? codigos.filter((c) => (c.sku + " " + c.name).toLowerCase().includes(busca.trim().toLowerCase())).slice(0, 20)
    : [];

  return (
    <div>
      <PageHeader
        title="Histórico de preços"
        subtitle="Evolução de preço por fornecedor ao longo do tempo, com base nas cotações lançadas."
      />
      {carregando ? (
        <Loading />
      ) : codigos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Ainda sem histórico. Assim que preços forem lançados em cotações, eles aparecem aqui.
        </div>
      ) : (
        <div>
          <div className="relative mb-4 max-w-md">
            <Input
              placeholder="Buscar por código ou descrição…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
            {sugestoes.length > 0 ? (
              <div className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg">
                {sugestoes.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      setProdutoId(c.id);
                      setBusca((c.sku || "#" + c.id) + " — " + c.name);
                    }}
                    className="block w-full border-b border-gray-100 px-3 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    <span className="font-mono text-xs text-gray-500">{c.sku || "#" + c.id}</span> — {c.name}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          {produtoId != null ? <Detalhe produtoId={produtoId} /> : null}
        </div>
      )}
    </div>
  );
}

function Detalhe({ produtoId }: { produtoId: number }) {
  const [rows, setRows] = useState<HistoricoPreco[] | null>(null);

  useEffect(() => {
    setRows(null);
    void (async () => {
      try {
        setRows(await api.historicoPrecos(produtoId));
      } catch {
        setRows([]);
      }
    })();
  }, [produtoId]);

  if (rows === null) return <Loading message="Carregando histórico…" />;
  if (rows.length === 0)
    return <div className="py-10 text-center text-sm text-gray-400">Esse produto ainda não tem preços registrados.</div>;

  const porFornecedor: Record<string, HistoricoPreco[]> = {};
  for (const r of rows) (porFornecedor[r.fornecedor_nome] ??= []).push(r);
  const nomes = Object.keys(porFornecedor);
  const cores = Object.fromEntries(nomes.map((n, i) => [n, CORES[i % CORES.length]]));

  return (
    <div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div dangerouslySetInnerHTML={{ __html: buildChart(porFornecedor, cores) }} />
        <div className="mt-2 flex flex-wrap gap-4">
          {nomes.map((n) => (
            <div key={n} className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: cores[n] }} />
              {n}
              {variacaoLabel(porFornecedor[n])}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <Table>
          <THead cols={["Data", "Fornecedor", "Cotação", "Preço", "Prazo"]} />
          <TBody>
            {rows.slice().reverse().map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <Cell className="text-xs text-gray-500">{fmtDateTime(r.registrado_em)}</Cell>
                <Cell>{r.fornecedor_nome}</Cell>
                <Cell>
                  <a href={`#/cotacoes/${r.cotacao_id}`} className="font-mono text-brand-600 hover:underline">
                    {r.cotacao_numero}
                  </a>
                </Cell>
                <Cell className="font-mono">{fmtMoney(r.preco_unitario)}</Cell>
                <Cell>{r.prazo_entrega_dias ? `${r.prazo_entrega_dias} dias` : "—"}</Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      </div>
    </div>
  );
}

function variacaoLabel(pontos: HistoricoPreco[]): string {
  if (pontos.length < 2) return "";
  const primeiro = pontos[0].preco_unitario;
  const ultimo = pontos[pontos.length - 1].preco_unitario;
  const delta = ((ultimo - primeiro) / primeiro) * 100;
  const sinal = delta > 0 ? "+" : "";
  return ` (${sinal}${delta.toFixed(1)}%)`;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function buildChart(porFornecedor: Record<string, HistoricoPreco[]>, cores: Record<string, string>): string {
  const W = 760;
  const H = 260;
  const PAD_L = 55;
  const PAD_B = 30;
  const PAD_T = 16;
  const PAD_R = 16;
  const allPontos = Object.values(porFornecedor).flat();
  const precos = allPontos.map((p) => p.preco_unitario);
  let min = Math.min(...precos);
  let max = Math.max(...precos);
  if (min === max) {
    min *= 0.9;
    max *= 1.1;
  }
  const pad = (max - min) * 0.1;
  min -= pad;
  max += pad;

  const datas = [...new Set(allPontos.map((p) => p.registrado_em))].sort();
  const xFor = (data: string) => {
    const idx = datas.indexOf(data);
    const n = Math.max(datas.length - 1, 1);
    return PAD_L + (idx / n) * (W - PAD_L - PAD_R);
  };
  const yFor = (preco: number) => PAD_T + (1 - (preco - min) / (max - min)) * (H - PAD_T - PAD_B);

  let gridHtml = "";
  for (let i = 0; i <= 4; i++) {
    const v = min + ((max - min) * i) / 4;
    const y = yFor(v);
    gridHtml += `<line x1="${PAD_L}" y1="${y}" x2="${W - PAD_R}" y2="${y}" stroke="#D7DACE" stroke-width="1"/>`;
    gridHtml += `<text x="${PAD_L - 8}" y="${y + 4}" text-anchor="end" font-size="10" fill="#8B948A">${v.toFixed(2)}</text>`;
  }

  let linesHtml = "";
  for (const [nome, pontos] of Object.entries(porFornecedor)) {
    const sorted = pontos.slice().sort((a, b) => (a.registrado_em > b.registrado_em ? 1 : -1));
    const pts = sorted.map((p) => `${xFor(p.registrado_em)},${yFor(p.preco_unitario)}`).join(" ");
    linesHtml += `<polyline points="${pts}" fill="none" stroke="${cores[nome]}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    for (const p of sorted) {
      linesHtml += `<circle cx="${xFor(p.registrado_em)}" cy="${yFor(p.preco_unitario)}" r="3.5" fill="${cores[nome]}"><title>${esc(nome)}: ${fmtMoney(p.preco_unitario)}</title></circle>`;
    }
  }

  const xLabels = datas.length <= 6 ? datas : [datas[0], datas[Math.floor(datas.length / 2)], datas[datas.length - 1]];
  const xLabelsHtml = xLabels
    .map((d) => `<text x="${xFor(d)}" y="${H - 8}" text-anchor="middle" font-size="10" fill="#8B948A">${fmtDate(d)}</text>`)
    .join("");

  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;" role="img">${gridHtml}${linesHtml}${xLabelsHtml}</svg>`;
}
