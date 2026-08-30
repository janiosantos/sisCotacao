// pages/fiscal/resultado.tsx - módulo Fiscal (ResultadoFiscal).

import { type FiscalResultado } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Badge, Table, TBody } from "../../ui/ui";

export function ResultadoFiscal({ r }: { r: FiscalResultado }) {
  const linha = (rot: string, val: string) => (
    <tr>
      <td className="px-4 py-2 text-xs text-gray-500">{rot}</td>
      <td className="px-4 py-2 text-right font-medium">{val}</td>
    </tr>
  );
  const memoria = r.memoria as Record<string, unknown>;
  const memoriaProduto = r.memoria_produto as Record<string, unknown> | null;

  return (
    <div className="max-w-2xl rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 font-semibold text-gray-900">
        Simulação — {r.cfop || "—"}{" "}
        <Badge tone={r.status_validacao === "erro" ? "red" : "green"}>
          {r.status_validacao === "erro" ? "ERROR (bloqueado)" : "ok"}
        </Badge>
      </h3>
      <Table>
        <TBody>
          {linha("NCM / CEST", `${r.ncm || "—"}${r.cest ? " · " + r.cest : ""}`)}
          {linha("CFOP", r.cfop || "—")}
          {linha(
            "CST / CSOSN",
            `${r.cst_icms || r.csosn || "—"}${r.cst_ibs || r.cst_cbs ? ` · IBS ${r.cst_ibs || "—"} / CBS ${r.cst_cbs || "—"}` : ""}`
          )}
          {linha("ICMS", `base ${fmtMoney(r.base_icms)} · ${r.aliquota_icms}% · ${fmtMoney(r.valor_icms)}`)}
          {linha("ICMS-ST", r.valor_icms_st ? `base ${fmtMoney(r.base_icms_st)} · ${r.aliquota_icms_st}% · ${fmtMoney(r.valor_icms_st)}` : "—")}
          {linha("PIS / COFINS", `${fmtMoney(r.valor_pis)} / ${fmtMoney(r.valor_cofins)}`)}
          {linha("IBS / CBS", `${fmtMoney(r.valor_ibs)} / ${fmtMoney(r.valor_cbs)}`)}
        </TBody>
      </Table>
      <p className="mt-2 text-xs text-gray-500">
        Regra: <span className="font-medium">{String(memoria.regra_nome || "configuração do produto")}</span>
        {memoria.versao ? ` · versão ${String(memoria.versao)}` : ""}
        {memoriaProduto ? ` · Produto: ${String(memoriaProduto.regra_nome || "")}` : ""}
      </p>
      {(r.problemas || []).length > 0 ? (
        <div className="mt-3">
          <h4 className="text-sm font-medium text-gray-700">Validação</h4>
          <ul className="mt-1 space-y-1">
            {(r.problemas || []).map((p, i) => (
              <li
                key={i}
                className={`text-xs ${
                  p.tipo === "ERROR" ? "text-red-600" : p.tipo === "WARNING" ? "text-amber-600" : "text-gray-500"
                }`}
              >
                <span className="font-semibold">{p.tipo}</span> · {p.campo} — {p.mensagem}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-medium text-gray-600">Árvore de decisão (por que essa regra?)</summary>
        <ul className="mt-2 space-y-1 text-xs text-gray-600">
          {(r.decisao || []).length === 0 ? (
            <li>—</li>
          ) : (
            (r.decisao || []).map((d, i) => (
              <li key={i}>
                <span className="font-semibold">{d.passo}</span>: {d.detalhe}
              </li>
            ))
          )}
        </ul>
      </details>
    </div>
  );
}


