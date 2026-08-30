// pages/historico.tsx — histórico de preços (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type ProdutoComHistorico } from "../api/client";
import { Input, Loading, PageHeader } from "../ui/ui";
import { Detalhe } from "./historico/detalhe";

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
