// pages/caixa/modal-localizar-pedido.tsx — localizar pedido finalizado no caixa.
import { useEffect, useState } from "react";
import { api, type OrcamentoLista } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { SearchModal } from "../../ui/search-modal";

export function ModalLocalizarPedido({ onClose, onSelecionar }: { onClose: () => void; onSelecionar: (id: number) => void }) {
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [rows, setRows] = useState<OrcamentoLista[]>([]);

  const buscar = () => {
    void api
      .listarOrcamentosFiltro({
        status: "finalizado",
        data_inicio: dataInicio || undefined,
        data_fim: dataFim || undefined,
      })
      .then(setRows)
      .catch(() => setRows([]));
  };

  useEffect(() => {
    buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataInicio, dataFim]);

  return (
    <SearchModal
      open
      title="Localizar pedido (finalizado)"
      columns={[
        { key: "numero", label: "Nº", render: (o) => o.numero },
        { key: "cliente", label: "Cliente", render: (o) => o.cliente || "—" },
        { key: "total", label: "Total", align: "right", render: (o) => fmtMoney(o.total) },
        { key: "n_itens", label: "Itens", align: "center", render: (o) => o.n_itens },
        { key: "criado_em", label: "Criado em", render: (o) => fmtDate(o.criado_em) },
      ]}
      data={rows}
      searchText={(o) => [o.numero, o.cliente].join(" ")}
      extra={
        <div className="mt-3 flex items-center gap-2 text-sm">
          <span className="font-bold text-gray-800">Filtrar por data:</span>
          <input
            type="date"
            value={dataInicio}
            onChange={(e) => setDataInicio(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
          <span>até</span>
          <input
            type="date"
            value={dataFim}
            onChange={(e) => setDataFim(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
        </div>
      }
      onClose={onClose}
      onSelect={(o) => onSelecionar(o.id)}
    />
  );
}