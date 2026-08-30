// pages/produtos/modal-importar-catalogo.tsx — importação do catálogo (JSON do scraper).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalImportarCatalogo({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [importando, setImportando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState<{ produtos: number; grupos: number; criados: number; atualizados: number } | null>(null);

  useEffect(() => {
    if (open) {
      setArquivo(null);
      setErro("");
      setResultado(null);
    }
  }, [open]);

  const importar = async () => {
    if (!arquivo) {
      toast("Selecione o arquivo JSON exportado pelo scraper", "error");
      return;
    }
    setImportando(true);
    setErro("");
    setResultado(null);
    try {
      const fd = new FormData();
      fd.append("file", arquivo);
      const res = await api.importarCatalogo(fd);
      setResultado(res);
      toast("Catálogo importado com sucesso", "success");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setImportando(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Importar catálogo (scraper)"
      footer={
        <>
          <Button onClick={onClose}>Fechar</Button>
          <Button variant="primary" onClick={() => void importar()} disabled={importando || !arquivo}>
            {importando ? "Importando…" : "Importar arquivo"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Field label="Arquivo JSON (output/catalogo.json)">
          <Input type="file" accept=".json,application/json" onChange={(e) => setArquivo(e.target.files?.[0] ?? null)} />
        </Field>
        <p className="text-xs text-gray-500">
          O scraper exporta o catálogo em JSON (100% local). A importação é idempotente: produtos já importados são
          atualizados, variantes sumidas são removidas e o histórico nunca é apagado.
        </p>
        {erro ? <p className="text-sm text-red-500">Erro: {erro}</p> : null}
        {resultado ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm">
            <p>
              <strong>{resultado.grupos}</strong> produtos ({resultado.produtos} itens) ·{" "}
              <strong>{resultado.criados}</strong> criados · <strong>{resultado.atualizados}</strong> atualizados
            </p>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}