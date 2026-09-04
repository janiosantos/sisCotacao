// pages/produtos/imagens.tsx — galeria de imagens do produto (upload, URL, capa, exclusão).
import { useEffect, useRef, useState } from "react";
import { api, type ProdutoCadastro } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Input } from "../../ui/ui";

export function Imagens({ produto, setProduto }: { produto: ProdutoCadastro; setProduto: (p: ProdutoCadastro) => void }) {
  const [url, setUrl] = useState("");
  const [baixando, setBaixando] = useState(false);
  const [importandoGaleria, setImportandoGaleria] = useState(false);
  const [galeriaDisponivel, setGaleriaDisponivel] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);
  const galeriaPopup = useRef<Window | null>(null);
  const galeriaOrigin = useRef("");

  const refresh = async () => {
    try {
      setProduto(await api.detalharProdutoCadastro(produto.id));
    } catch {
      /* silêncio */
    }
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !files.length) return;
    const count = files.length;
    const fd = new FormData();
    for (let i = 0; i < files.length; i++) fd.append("files", files[i]);
    try {
      await api.enviarImagensProduto(produto.id, fd);
      await refresh();
      toast(`${count} imagem(ns) enviada(s)`, "success");
    } catch (e) {
      toast("Erro no upload: " + (e as Error).message, "error");
    }
    e.target.value = "";
  };

  const baixarUrl = async () => {
    if (!url.trim()) {
      toast("Informe a URL", "error");
      return;
    }
    setBaixando(true);
    try {
      const res = await api.baixarImagensUrl(produto.id, url.trim());
      await refresh();
      toast(`${res.total} imagem(ns) baixada(s)`, "success");
      if (res.erros && res.erros.length) toast(`Erros: ${res.erros.slice(0, 3).join(" | ")}`, "error");
    } catch (e) {
      toast("Erro ao baixar: " + (e as Error).message, "error");
    } finally {
      setBaixando(false);
    }
  };

  const imgs = produto.imagens || [];

  useEffect(() => {
    api.statusGaleriaProdutos().then((value) => setGaleriaDisponivel(value.available)).catch(() => setGaleriaDisponivel(false));
  }, []);

  useEffect(() => {
    const onMessage = async (event: MessageEvent) => {
      if (
        event.origin !== galeriaOrigin.current ||
        event.source !== galeriaPopup.current ||
        event.data?.type !== "siscom-gallery-selection" ||
        !Array.isArray(event.data.imageIds)
      ) return;
      const imageIds = event.data.imageIds.filter(
        (value: unknown): value is number => Number.isInteger(value) && Number(value) > 0
      );
      if (!imageIds.length) return;
      setImportandoGaleria(true);
      try {
        const result = await api.importarImagensGaleria(produto.id, imageIds);
        await refresh();
        const complemento = result.deduplicadas ? `; ${result.deduplicadas} já existia(m)` : "";
        toast(`${result.total} imagem(ns) adicionada(s)${complemento}`, "success");
      } catch (error) {
        toast("Erro ao importar da galeria: " + (error as Error).message, "error");
      } finally {
        setImportandoGaleria(false);
        galeriaPopup.current = null;
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [produto.id]);

  const abrirGaleria = async () => {
    try {
      const status = await api.statusGaleriaProdutos();
      setGaleriaDisponivel(status.available);
      if (!status.available) {
        toast("A galeria preservada ainda não está disponível", "error");
        return;
      }
      const target = new URL(status.url, window.location.href);
      target.searchParams.set("return_origin", window.location.origin);
      galeriaOrigin.current = target.origin;
      galeriaPopup.current = window.open(
        target.toString(),
        "siscom-galeria-produtos",
        "popup=yes,width=1320,height=860,resizable=yes,scrollbars=yes"
      );
      if (!galeriaPopup.current) toast("Permita pop-ups para abrir a galeria", "error");
    } catch (error) {
      toast("Não foi possível abrir a galeria: " + (error as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        <label className="inline-flex cursor-pointer items-center justify-center rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          Enviar arquivos
          <input ref={uploadRef} type="file" accept="image/*" multiple hidden onChange={onUpload} />
        </label>
        <Input className="flex-1" placeholder="URL da página do produto ou imagem direta" value={url} onChange={(e) => setUrl(e.target.value)} />
        <Button variant="primary" onClick={() => void baixarUrl()} disabled={baixando}>
          {baixando ? "Baixando…" : "Baixar da internet"}
        </Button>
        <Button
          variant="secondary"
          onClick={() => void abrirGaleria()}
          disabled={!galeriaDisponivel || importandoGaleria}
          title={galeriaDisponivel ? "Selecionar imagens preservadas do catálogo anterior" : "Galeria ainda não instalada"}
        >
          {importandoGaleria ? "Importando…" : "Escolher da galeria"}
        </Button>
      </div>

      <p className="mb-4 text-xs text-gray-500">
        A galeria preserva as fotos do catálogo anterior. Pesquise pelo nome, categoria, subcategoria ou marca e selecione até 12 imagens.
      </p>

      {imgs.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">Nenhuma imagem. Envie arquivos ou informe a URL de uma página do produto.</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {imgs.map((im, i) => (
            <div key={im.id} className="relative rounded-lg border border-gray-200 bg-white p-2">
              <img src={im.url} loading="lazy" alt="" className="h-24 w-full object-contain" />
              {i === 0 ? <span className="absolute left-1 top-1 rounded bg-brand-600 px-1.5 py-0.5 text-[10px] font-medium text-white">Capa</span> : null}
              {i > 0 && (
                <button
                  className="absolute right-1 top-1 rounded bg-white px-1 text-gray-500 shadow hover:text-amber-500"
                  title="Definir como imagem de capa"
                  onClick={async () => {
                    try {
                      await api.definirCapaImagem(produto.id, im.id);
                      await refresh();
                      toast("Imagem de capa atualizada", "success");
                    } catch (e) {
                      toast("Erro ao definir capa: " + (e as Error).message, "error");
                    }
                  }}
                >
                  ★
                </button>
              )}
              <button
                className="absolute bottom-1 right-1 rounded bg-white px-1 text-gray-500 shadow hover:text-red-600"
                title="Excluir imagem"
                onClick={async () => {
                  try {
                    await api.excluirImagem(im.id);
                    await refresh();
                  } catch (e) {
                    toast("Erro ao excluir imagem: " + (e as Error).message, "error");
                  }
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
