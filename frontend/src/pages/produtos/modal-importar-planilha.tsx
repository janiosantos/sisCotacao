// pages/produtos/modal-importar-planilha.tsx — importação de lista de produtos por CSV/XLSX.
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

type Resultado = {
  total: number;
  criados: number;
  atualizados: number;
  erros: number;
  erros_detalhe: { linha: number; motivo: string }[];
};

export function ModalImportarPlanilha({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [importando, setImportando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState<Resultado | null>(null);

  useEffect(() => {
    if (open) {
      setArquivo(null);
      setErro("");
      setResultado(null);
    }
  }, [open]);

  const importar = async () => {
    if (!arquivo) {
      toast("Selecione o arquivo CSV ou XLSX", "error");
      return;
    }
    setImportando(true);
    setErro("");
    setResultado(null);
    try {
      const fd = new FormData();
      fd.append("file", arquivo);
      const res = await api.importarPlanilha(fd);
      setResultado(res);
      toast(`Importação concluída: ${res.criados} criados · ${res.atualizados} atualizados · ${res.erros} erros`, res.erros ? "warn" : "success");
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
      title="Importar produtos (planilha)"
      footer={
        <>
          <Button onClick={onClose}>Fechar</Button>
          <Button variant="primary" onClick={() => void importar()} disabled={importando || !arquivo}>
            {importando ? "Importando…" : "Importar planilha"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Field label="Arquivo CSV ou XLSX">
          <Input type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(e) => setArquivo(e.target.files?.[0] ?? null)} />
        </Field>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600">
          <p className="mb-1 font-semibold text-gray-700">Formato da planilha</p>
          <p>1 linha de cabeçalho com a coluna obrigatória <strong>DESCRICAO</strong> e as opcionais:</p>
          <p className="mt-1 font-mono">MARCA · GRUPO · SUBGRUPO · CATEGORIA · SUBCATEGORIA · FAMILIA</p>
          <p className="mt-1">
            Ordem e caixa das colunas são livres. Grupo/subgrupo/categoria/subcategoria/família/marca são
            criados automaticamente quando não existem. Produtos entram como <strong>rascunho</strong> (revisar
            antes de publicar).
          </p>
        </div>
        {erro ? <p className="text-sm text-red-500">Erro: {erro}</p> : null}
        {resultado ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm">
            <p>
              <strong>{resultado.total}</strong> linhas · <strong>{resultado.criados}</strong> criados ·{" "}
              <strong>{resultado.atualizados}</strong> já existentes · <strong>{resultado.erros}</strong> erros
            </p>
            {resultado.erros_detalhe.length ? (
              <ul className="mt-1 list-inside list-disc text-xs text-red-600">
                {resultado.erros_detalhe.slice(0, 10).map((e, i) => (
                  <li key={i}>
                    Linha {e.linha}: {e.motivo}
                  </li>
                ))}
                {resultado.erros_detalhe.length > 10 ? <li>… e mais {resultado.erros_detalhe.length - 10}.</li> : null}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}