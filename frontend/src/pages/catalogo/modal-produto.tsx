// pages/catalogo/modal-produto.tsx — detalhe do produto com adição à cotação.
import { useEffect, useState } from "react";
import { api, type ProdutoResumo } from "../../api/client";
import * as Cart from "../../cart";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Input, Loading, Modal } from "../../ui/ui";

export function ModalProduto({ produtoId, onClose }: { produtoId: number; onClose: () => void }) {
  const [p, setP] = useState<ProdutoResumo | null>(null);
  const [qty, setQty] = useState(1);
  const [imgs, setImgs] = useState<string[]>([]);
  const [main, setMain] = useState("");

  useEffect(() => {
    void api
      .detalharProduto(produtoId)
      .then((prod) => {
        setP(prod);
        const arr = (prod as ProdutoResumo & { image_urls?: string[] }).image_urls || [];
        setImgs(arr);
        setMain(arr.length ? arr[0] : "");
      })
      .catch(() => toast("Erro ao carregar produto", "error"));
  }, [produtoId]);

  const adicionar = () => {
    if (!p) return;
    const q = Math.max(1, qty || 1);
    Cart.addItem(p.id, q, {
      name: p.name || "",
      spec: [(p as ProdutoResumo & { color?: string }).color].filter(Boolean).join(", "),
      brand: p.brand || "",
      price: p.price || 0,
      imagem_url: main || "",
    });
    onClose();
    toast(`${q} item(ns) adicionado(s) à sua cotação`, "success");
  };

  return (
    <Modal open onClose={onClose} title="Produto" footer={
      <>
        <Button onClick={onClose}>Fechar</Button>
        <Button variant="primary" onClick={adicionar}>
          Adicionar à cotação
        </Button>
      </>
    }>
      {!p ? (
        <Loading />
      ) : (
        <div>
          {main ? <img src={main} alt="" className="mx-auto max-h-56 object-contain" /> : null}
          {imgs.length > 1 && (
            <div className="mt-2 flex gap-2">
              {imgs.map((u, i) => (
                <img
                  key={i}
                  src={u}
                  onClick={() => setMain(u)}
                  className={`h-12 w-12 cursor-pointer rounded border object-contain ${main === u ? "border-brand-500" : "border-gray-200"}`}
                  alt=""
                />
              ))}
            </div>
          )}
          <p className="mt-3 font-mono text-xs text-gray-500">{p.sku || "#" + p.id}</p>
          <h3 className="text-base font-semibold text-gray-900">{p.name}</h3>
          {p.brand ? <div className="text-sm text-gray-500">Marca: {p.brand}</div> : null}
          {(p as ProdutoResumo & { color?: string }).color ? (
            <div className="text-sm text-gray-500">Cor: {(p as ProdutoResumo & { color?: string }).color}</div>
          ) : null}
          <div className="mt-2 text-lg font-semibold text-gray-900">{fmtMoney(p.price)}</div>
          {p.pix_price ? <div className="text-sm font-semibold text-emerald-600">PIX: {fmtMoney(p.pix_price)}</div> : null}
          {p.installment ? <div className="text-sm text-gray-500">{p.installment}</div> : null}
          <div className="mt-4 flex items-center gap-2">
            <Input type="number" min={1} step={1} value={qty} onChange={(e) => setQty(parseInt(e.target.value, 10) || 1)} className="w-24" />
            <span className="text-sm text-gray-500">unidade(s)</span>
          </div>
        </div>
      )}
    </Modal>
  );
}