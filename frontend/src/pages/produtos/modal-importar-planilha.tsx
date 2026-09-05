// pages/produtos/modal-importar-planilha.tsx — importação de lista de produtos por CSV/XLSX.
import { useEffect, useState } from "react";
import { api, mensagemErro } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

type Resultado = {
  importacao_id: number;
  duplicado: boolean;
  total: number;
  criados: number;
  atualizados: number;
  erros: number;
  erros_detalhe: { linha: number; motivo: string; sugestao: string }[];
  relatorio_erros_url: string | null;
};

export function ModalImportarPlanilha({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [importando, setImportando] = useState(false);
  const [baixando, setBaixando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState<Resultado | null>(null);

  useEffect(() => {
    if (open) {
      setArquivo(null);
      setErro("");
      setResultado(null);
      setBaixando(false);
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

  const baixarRejeicoes = async () => {
    if (!resultado?.erros) return;
    setBaixando(true);
    setErro("");
    try {
      const blob = await api.baixarErrosImportacaoProdutos(resultado.importacao_id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `produtos-nao-importados-${resultado.importacao_id}.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setBaixando(false);
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
          <p>1 linha de cabeçalho com <strong>DESCRIÇÃO</strong>/<strong>DESCRICAO</strong>, <strong>NOME</strong> ou <strong>PRODUTO</strong> e as opcionais:</p>
          <p className="mt-1 font-mono">MARCA · GRUPO · SUBGRUPO · CATEGORIA · SUBCATEGORIA · FAMILIA</p>
          <p className="mt-1">
            Ordem e caixa das colunas são livres. Grupo/subgrupo/categoria/subcategoria/família/marca são
            localizados sem diferenciar acentos ou maiúsculas e criados automaticamente quando não existem.
            Produtos entram como <strong>rascunho</strong> (revisar antes de publicar).
          </p>
          <p className="mt-1">Linhas com erro são ignoradas sem interromper as demais e ficam disponíveis em uma planilha de correção.</p>
        </div>
        {erro ? <p className="text-sm text-red-500">Erro: {erro}</p> : null}
        {resultado ? (
          <div className={resultado.erros ? "rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm" : "rounded-lg border border-green-200 bg-green-50 p-3 text-sm"}>
            {resultado.duplicado ? (
              <p className="mb-1 font-medium text-slate-700">Este arquivo já havia sido processado; abaixo está o resultado auditado do primeiro envio.</p>
            ) : null}
            <p>
              <strong>{resultado.total}</strong> linhas · <strong>{resultado.criados}</strong> criados ·{" "}
              <strong>{resultado.atualizados}</strong> já existentes (ignorados) · <strong>{resultado.erros}</strong> não importados
            </p>
            {resultado.erros_detalhe.length ? (
              <div className="mt-2 space-y-2">
                <p className="text-xs text-amber-900">As linhas válidas foram importadas. Corrija somente as rejeitadas e envie a planilha novamente.</p>
                <ul className="max-h-40 list-inside list-disc overflow-y-auto text-xs text-red-700">
                  {resultado.erros_detalhe.slice(0, 10).map((e, i) => (
                    <li key={i}>
                      Linha {e.linha}: {e.motivo} <span className="text-slate-600">{e.sugestao}</span>
                    </li>
                  ))}
                  {resultado.erros_detalhe.length > 10 ? <li>… e mais {resultado.erros_detalhe.length - 10}.</li> : null}
                </ul>
                <Button type="button" variant="secondary" size="sm" onClick={() => void baixarRejeicoes()} disabled={baixando}>
                  {baixando ? "Preparando planilha…" : "Baixar planilha de não importados"}
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
