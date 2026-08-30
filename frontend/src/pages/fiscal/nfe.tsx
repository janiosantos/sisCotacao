// pages/fiscal/nfe.tsx - módulo Fiscal (Nfe).

import { useEffect, useState } from "react";
import { api, type NfeEntrada, type NfeSaida } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { Badge, Cell, Loading, Table, TBody, THead } from "../../ui/ui";

export function Nfe() {
  const [sub, setSub] = useState<"saida" | "entrada">("saida");
  const [saida, setSaida] = useState<NfeSaida[]>([]);
  const [entrada, setEntrada] = useState<NfeEntrada[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    setCarregando(true);
    if (sub === "saida") {
      void api
        .listarNfeSaida()
        .then(setSaida)
        .catch(() => setSaida([]))
        .finally(() => setCarregando(false));
    } else {
      void api
        .listarNfeEntrada()
        .then(setEntrada)
        .catch(() => setEntrada([]))
        .finally(() => setCarregando(false));
    }
  }, [sub]);

  return (
    <div>
      <div className="mb-5 flex flex-wrap gap-2 border-b border-gray-200">
        {(["saida", "entrada"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setSub(s)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              sub === s ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {s === "saida" ? "Saída" : "Entrada"}
          </button>
        ))}
      </div>

      {carregando ? (
        <Loading />
      ) : sub === "saida" ? (
        saida.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
            Nenhuma NF-e de saída
          </div>
        ) : (
          <Table>
            <THead cols={["Nº", "Cliente", "Valor", "Status", "Data"]} />
            <TBody>
              {saida.map((n) => (
                <tr key={n.id} className="hover:bg-gray-50">
                  <Cell className="font-mono">{n.numero}</Cell>
                  <Cell>{n.cliente_nome}</Cell>
                  <Cell>{fmtMoney(n.valor)}</Cell>
                  <Cell>
                    <Badge tone={n.status === "autorizada" ? "green" : "gray"}>{n.status}</Badge>
                  </Cell>
                  <Cell className="text-xs">{fmtDate(n.criado_em)}</Cell>
                </tr>
              ))}
            </TBody>
          </Table>
        )
      ) : entrada.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhuma NF-e de entrada
        </div>
      ) : (
        <Table>
          <THead cols={["Chave", "Fornecedor", "Valor", "Emissão"]} />
          <TBody>
            {entrada.map((n) => (
              <tr key={n.id} className="hover:bg-gray-50">
                <Cell className="font-mono text-xs">{n.chave}</Cell>
                <Cell>{n.fornecedor_nome}</Cell>
                <Cell>{fmtMoney(n.valor)}</Cell>
                <Cell className="text-xs">{fmtDate(n.data_emissao)}</Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}


