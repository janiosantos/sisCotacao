// pages/precos/modal-gerar-precos.tsx - módulo Preços (ModalGerarPrecos).

import { useEffect, useState } from "react";
import { api, type ItemPreviaReajuste, type PreviaReajuste, type ReajusteResultado, type TabelaPreco } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Cell, Field, Input, Loading, Modal, Table, TBody, THead } from "../../ui/ui";

export function ModalGerarPrecos({
  tab,
  onClose,
  onApplied,
}: {
  tab: TabelaPreco | null;
  onClose: () => void;
  onApplied: () => void;
}) {
  const [margem, setMargem] = useState("0");
  const [markup, setMarkup] = useState("0");
  const [previa, setPrevia] = useState<PreviaReajuste | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [aplicando, setAplicando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (tab) {
      setMargem(String(tab.margem_padrao || 0));
      setMarkup(String(tab.markup || 0));
      setPrevia(null);
      setErro("");
    }
  }, [tab]);

  const verPrevia = async () => {
    if (!tab) return;
    const params: Record<string, unknown> = {};
    const m = parseFloat(margem.replace(",", "."));
    const k = parseFloat(markup.replace(",", "."));
    if (!isNaN(m)) params.margem = m;
    if (!isNaN(k)) params.markup = k;
    setCarregando(true);
    setErro("");
    setPrevia(null);
    try {
      const r = await api.previaReajusteTabela(tab.id, params);
      setPrevia(r);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  const aplicar = async () => {
    if (!tab) return;
    const params: Record<string, unknown> = { confirmado: true };
    const m = parseFloat(margem.replace(",", "."));
    const k = parseFloat(markup.replace(",", "."));
    if (!isNaN(m)) params.margem = m;
    if (!isNaN(k)) params.markup = k;
    setAplicando(true);
    try {
      const res: ReajusteResultado = await api.reajustarTabela(tab.id, params);
      toast(`${res.aplicados} preços aplicados (${res.sem_custo} sem custo)`, "success");
      onClose();
      onApplied();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setAplicando(false);
    }
  };

  return (
    <Modal
      open={tab !== null}
      onClose={onClose}
      title={`Reajustar preços — ${tab?.nome ?? ""}`}
      wide
      footer={<Button onClick={onClose}>Fechar</Button>}
    >
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Calcula o preço sugerido pelo motor (custo líquido do Fiscal → margem/markup), mostra a prévia e, após
          confirmação, aplica e registra o histórico.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Margem % (preço = custo ÷ (1 − margem))">
            <Input type="number" step="0.1" value={margem} onChange={(e) => setMargem(e.target.value)} />
          </Field>
          <Field label="Markup % (preço = custo × (1 + markup))">
            <Input type="number" step="0.1" value={markup} onChange={(e) => setMarkup(e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <Button onClick={() => void verPrevia()} disabled={carregando}>
            Ver prévia
          </Button>
          <Button variant="primary" onClick={() => void aplicar()} disabled={!previa || !previa.itens.length || aplicando}>
            {aplicando ? "Aplicando…" : "Aplicar (aprovar)"}
          </Button>
        </div>

        {carregando ? <Loading message="Calculando prévia…" /> : null}
        {erro ? <div className="py-4 text-center text-sm text-gray-400">Erro: {erro}</div> : null}
        {previa && previa.itens.length === 0 && !carregando ? (
          <div className="py-4 text-center text-sm text-gray-400">Nenhum produto com custo para reajustar.</div>
        ) : null}
        {previa && previa.itens.length > 0 ? (
          <div>
            <p className="mb-2 text-xs text-gray-500">
              {previa.total} item(ns) · margem {previa.margem}% · markup {previa.markup}%
            </p>
            <Table>
              <THead cols={["Produto", "Custo líquido", "Atual", "Sugerido", "Margem"]} />
              <TBody>
                {previa.itens.slice(0, 60).map((i: ItemPreviaReajuste) => (
                  <tr key={i.produto_id} className="hover:bg-gray-50">
                    <Cell>
                      <span className="font-medium">{i.produto_nome}</span>
                      {i.sku ? <div className="font-mono text-xs text-gray-400">{i.sku}</div> : null}
                    </Cell>
                    <Cell>{i.custo_liquido != null ? fmtMoney(i.custo_liquido) : "—"}</Cell>
                    <Cell>{fmtMoney(i.preco_atual)}</Cell>
                    <Cell className="font-medium">{i.preco_sugerido != null ? fmtMoney(i.preco_sugerido) : "—"}</Cell>
                    <Cell>{i.margem_efetiva_pct != null ? i.margem_efetiva_pct.toFixed(2).replace(".", ",") + "%" : "—"}</Cell>
                  </tr>
                ))}
              </TBody>
            </Table>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}


