// pages/produtos/modal-importar-lote.tsx — importação em lote com prévia (MDM-006).
import { useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Modal, Textarea } from "../../ui/ui";

type PreviewLinha = { linha: number; status: string; motivo?: string };

export function ModalImportarLote({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [texto, setTexto] = useState("");
  const [preview, setPreview] = useState<PreviewLinha[] | null>(null);
  const [resultado, setResultado] = useState<{ criados: number; atualizados: number; erros: number; duplicado: boolean } | null>(null);
  const [processando, setProcessando] = useState(false);

  const parseItens = (): Record<string, unknown>[] | null => {
    try {
      const arr = JSON.parse(texto);
      if (!Array.isArray(arr)) throw new Error("esperava uma lista JSON");
      return arr;
    } catch (e) {
      toast("JSON inválido: " + (e as Error).message, "error");
      return null;
    }
  };

  const fazerPreview = async () => {
    const itens = parseItens();
    if (!itens) return;
    setProcessando(true);
    setPreview(null);
    setResultado(null);
    try {
      setPreview((await api.previewImportacaoProdutos(itens)).linhas);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setProcessando(false);
    }
  };

  const importar = async () => {
    const itens = parseItens();
    if (!itens) return;
    setProcessando(true);
    try {
      const r = await api.importarProdutos(itens, `lote-${Date.now()}.json`);
      setResultado({ criados: r.criados, atualizados: r.atualizados, erros: r.erros, duplicado: r.duplicado });
      toast(
        r.duplicado
          ? "Lote já importado antes (idempotente) — nada duplicado"
          : `${r.criados} criado(s), ${r.atualizados} já existiam, ${r.erros} erro(s)`,
        r.erros ? "warn" : "success"
      );
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setProcessando(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Importar produtos em lote"
      wide
      footer={
        <>
          <Button onClick={onClose}>Fechar</Button>
          <Button onClick={() => void fazerPreview()} disabled={processando || !texto.trim()}>
            {processando ? "…" : "Prévia"}
          </Button>
          <Button variant="primary" onClick={() => void importar()} disabled={processando || !texto.trim()}>
            Importar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Cole uma lista JSON de produtos. Campos aceitos: <code>nome</code>* (obrigatório), <code>sku</code>,{" "}
          <code>ean</code>, <code>marca</code>, <code>preco</code>, <code>unidade_venda</code>. A importação é
          idempotente (mesmo lote não duplica) e cria os produtos como <b>rascunho</b> (publique depois).
        </p>
        <Field label="JSON (lista)">
          <Textarea
            rows={8}
            spellCheck={false}
            className="font-mono text-xs"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder='[{"nome":"Cabo 2,5mm","sku":"CAB-25","ean":"7891000000001","preco":3.2}]'
          />
        </Field>
        {preview ? (
          <div className="rounded-md border border-gray-200 bg-white p-3 text-sm">
            <div className="mb-2 text-xs font-semibold text-gray-500">
              Prévia: {preview.length} linha(s) · {preview.filter((l) => l.status === "erro").length} erro(s)
            </div>
            {preview.map((l) => (
              <div key={l.linha} className="flex gap-2 border-b border-gray-100 py-1 text-xs last:border-0">
                <span className="font-mono text-gray-400">#{l.linha}</span>
                <span className={l.status === "erro" ? "text-red-600" : "text-emerald-600"}>{l.status}</span>
                {l.motivo ? <span className="text-gray-500">{l.motivo}</span> : null}
              </div>
            ))}
          </div>
        ) : null}
        {resultado ? (
          <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
            {resultado.duplicado
              ? "Lote já processado anteriormente (nada duplicado)."
              : `${resultado.criados} criado(s) · ${resultado.atualizados} já existiam · ${resultado.erros} erro(s).`}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}