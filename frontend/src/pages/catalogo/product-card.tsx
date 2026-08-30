// pages/catalogo/product-card.tsx — card plano de produto do catálogo.
import { type ProdutoResumo } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Badge, Button } from "../../ui/ui";

export function ProductCard({
  prod,
  qty,
  onSetQty,
  onOpen,
}: {
  prod: ProdutoResumo;
  qty: number;
  onSetQty: (q: number) => void;
  onOpen: () => void;
}) {
  return (
    <article className={`overflow-hidden rounded-lg border bg-white shadow-sm ${qty > 0 ? "border-brand-500 ring-1 ring-brand-500" : "border-gray-200"}`}>
      <div className="flex h-40 cursor-pointer items-center justify-center bg-gray-50 p-3" onClick={onOpen}>
        {prod.imagem_url ? (
          <img src={prod.imagem_url} loading="lazy" alt="" className="max-h-full max-w-full object-contain" />
        ) : (
          <span className="font-mono text-xs text-gray-400">sem imagem</span>
        )}
      </div>
      <div className="p-3">
        <p className="font-mono text-xs text-gray-500">
          {prod.classe_abc ? <Badge tone="blue">{prod.classe_abc}</Badge> : null} {prod.sku || "#" + prod.id}
        </p>
        <p className="mt-1 line-clamp-2 text-sm font-medium text-gray-900">{prod.name}</p>
        {prod.spec ? <p className="mt-0.5 line-clamp-1 text-xs text-gray-500">{prod.spec}</p> : null}
        {prod.brand ? <p className="text-xs text-gray-400">{prod.brand}</p> : null}
        <div className="mt-2 flex items-center justify-between">
          <p className="text-base font-semibold text-gray-900">{fmtMoney(prod.price)}</p>
          {prod.package_label ? <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{prod.package_label}</span> : null}
        </div>
        {qty > 0 ? <p className="mt-1 text-xs text-brand-700">{qty} no carrinho</p> : null}
      </div>
      <div className="flex items-center justify-between border-t border-gray-100 px-3 py-2">
        <Button size="sm" variant="ghost" onClick={() => onSetQty(Math.max(0, qty - 1))}>
          –
        </Button>
        <input
          type="number"
          min={0}
          className="w-16 rounded-md border border-gray-300 px-2 py-1 text-center text-sm focus:border-brand-500 focus:outline-none"
          value={qty}
          onChange={(e) => onSetQty(Math.max(0, parseInt(e.target.value, 10) || 0))}
        />
        <Button size="sm" variant="ghost" onClick={() => onSetQty(qty + 1)}>
          +
        </Button>
      </div>
    </article>
  );
}