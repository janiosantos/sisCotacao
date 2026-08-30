// pages/produtos/modal-importar-url.tsx — cadastro de produto a partir de URL
// (lê a página, cria família/atributos e baixa fotos; PreviewRow de apoio).
import { useEffect, useState } from "react";
import { api, type ProdutoPreview } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function PreviewRow({ k, v }: { k: string; v?: string | null }) {
  if (!v) return null;
  return (
    <div className="flex gap-2 border-b border-gray-100 py-1.5">
      <span className="w-36 text-gray-500">{k}</span>
      <span className="font-medium">{v}</span>
    </div>
  );
}

export function ModalImportarUrl({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [parsed, setParsed] = useState<ProdutoPreview | null>(null);
  const [analisando, setAnalisando] = useState(false);
  const [cadastrando, setCadastrando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (open) {
      setUrl("");
      setParsed(null);
      setErro("");
    }
  }, [open]);

  const analisar = async () => {
    if (!url.trim()) {
      toast("Informe a URL do produto", "error");
      return;
    }
    setAnalisando(true);
    setErro("");
    setParsed(null);
    try {
      setParsed(await api.parseUrlProduto(url.trim()));
      toast("Produto identificado", "success");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setAnalisando(false);
    }
  };

  const cadastrar = async () => {
    if (!parsed) return;
    setCadastrando(true);
    try {
      const res = await api.criarProdutoPorUrl(parsed.url);
      onClose();
      toast(`Produto cadastrado (${res.imagens_baixadas} foto(s) baixada(s))`, "success");
      if (res.imagens_erros) toast(`${res.imagens_erros} foto(s) não puderam ser baixadas`, "error");
      location.hash = `#/produtos/${res.id}`;
    } catch (e) {
      toast("Erro ao cadastrar: " + (e as Error).message, "error");
      setCadastrando(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Cadastrar a partir de URL"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button onClick={() => void analisar()} disabled={analisando}>
            {analisando ? "Analisando…" : "Analisar URL"}
          </Button>
          {parsed && (
            <Button variant="primary" onClick={() => void cadastrar()} disabled={cadastrando}>
              {cadastrando ? "Cadastrando…" : "Cadastrar produto"}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-3">
        <Field label="URL do produto">
          <Input placeholder="https://www.casadoeletricistasc.com.br/..." value={url} onChange={(e) => setUrl(e.target.value)} />
        </Field>
        <p className="text-xs text-gray-500">O sistema lê a página e cria automaticamente a família, os atributos e baixa as fotos. Você confere o resultado antes de confirmar.</p>
        {erro ? <p className="text-sm text-gray-400">Erro: {erro}</p> : null}
        {parsed && (
          <div className="rounded-lg border border-gray-200 p-3 text-sm">
            <PreviewRow k="Produto" v={parsed.nome} />
            <PreviewRow k="Marca" v={parsed.marca} />
            <PreviewRow k="SKU / EAN" v={[parsed.sku, parsed.ean].filter(Boolean).join(" / ")} />
            <PreviewRow k="Família" v={parsed.familia_nome} />
            <PreviewRow k="Preço" v={parsed.preco != null ? fmtMoney(parsed.preco) : "—"} />
            <PreviewRow k="À vista (PIX)" v={parsed.preco_pix != null ? fmtMoney(parsed.preco_pix) : "—"} />
            <PreviewRow k="De" v={parsed.preco_de != null ? fmtMoney(parsed.preco_de) : "—"} />
            <PreviewRow k="Parcelamento" v={parsed.parcelamento} />
            <PreviewRow k="Fotos" v={String(parsed.fotos)} />
            {(parsed.atributos || []).length > 0 && (
              <div className="flex gap-2 border-t border-gray-100 py-2">
                <span className="w-36 text-gray-500">Atributos</span>
                <span>{parsed.atributos?.map((a) => `${a.label}: ${a.valor}`).join(" · ")}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}