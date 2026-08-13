// ConsultarPreco.tsx — modal "Consultar preço" (padrão Protheus), em React.

import { useEffect, useRef, useState } from "react";
import { api, type ProdutoResumo } from "../api/client";
import { fmtMoney } from "../ui/format";
import { LegacyModalShell, inputStyle } from "../legacy-kit";

export default function ConsultarPreco({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [termo, setTermo] = useState("");
  const [itens, setItens] = useState<ProdutoResumo[]>([]);
  const [carregando, setCarregando] = useState(false);
  const buscaRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) setTimeout(() => buscaRef.current?.focus(), 0);
  }, [open]);

  const buscar = async () => {
    const q = termo.trim();
    if (!q) {
      setItens([]);
      return;
    }
    setCarregando(true);
    try {
      const res = await api.listarProdutos({ q, limit: 20, agrupado: 0 });
      setItens(res.items.filter((i): i is ProdutoResumo => "price" in i));
    } catch {
      setItens([]);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <LegacyModalShell open={open} title="Consultar Preço" onClose={onClose} width={520}>
      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        <input
          ref={buscaRef}
          className="lg-input"
          style={{ flex: 1 }}
          placeholder="Produto, SKU ou EAN…"
          value={termo}
          onChange={(e) => setTermo(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void buscar()}
        />
        <button className="lg-btn lg-btn--primary" onClick={() => void buscar()}>
          Buscar
        </button>
      </div>
      {carregando ? (
        <div style={{ fontSize: 12, color: "#5b6b7c" }}>Buscando…</div>
      ) : itens.length ? (
        <div style={{ border: "1px solid #c8d0da", maxHeight: 320, overflow: "auto" }}>
          {itens.map((p) => (
            <div
              key={p.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 10,
                padding: "6px 10px",
                borderBottom: "1px solid #e2e8ef",
                fontSize: 12.5,
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600 }}>{p.name}</div>
                <div style={{ fontFamily: inputStyle.fontFamily, fontSize: 10.5, color: "#5b6b7c" }}>
                  {p.sku || "#" + p.id}
                </div>
              </div>
              <strong style={{ whiteSpace: "nowrap", color: "#1b4dab" }}>{fmtMoney(p.price)}</strong>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ fontSize: 12, color: "#5b6b7c" }}>Informe um termo para consultar preços.</div>
      )}
    </LegacyModalShell>
  );
}
