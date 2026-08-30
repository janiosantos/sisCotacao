// pages/financeiro/anexo-button.tsx — anexos (nota/boleto) de um lançamento.
import { useRef, useState } from "react";
import { api, type ContaAnexo } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Field, Modal } from "../../ui/ui";

export function AnexoButton({ tabela, contaId }: { tabela: "pagar" | "receber"; contaId: number }) {
  const [anexos, setAnexos] = useState<ContaAnexo[] | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const abrir = async () => {
    try {
      setAnexos(await api.listarAnexos(tabela, contaId));
    } catch {
      setAnexos([]);
    }
  };

  const subir = async (f: File | undefined) => {
    if (!f) return;
    try {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("tipo", "documento");
      await api.anexarDocumento(tabela, contaId, fd);
      toast("Anexo salvo", "success");
      await abrir();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <>
      <Button size="sm" variant="ghost" onClick={() => void abrir()} title="Anexos (nota/boleto)">
        📎
      </Button>
      <Modal
        open={anexos != null}
        onClose={() => setAnexos(null)}
        title="Anexos do lançamento"
        footer={<Button onClick={() => setAnexos(null)}>Fechar</Button>}
      >
        <div className="space-y-3">
          <Field label="Novo anexo (PDF/imagem)">
            <input type="file" accept="image/*,.pdf" ref={fileRef} onChange={(e) => void subir(e.target.files?.[0])} className="text-sm" />
          </Field>
          {(anexos || []).length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-400">Nenhum anexo.</p>
          ) : (
            <div className="space-y-1">
              {(anexos || []).map((a) => (
                <div key={a.id} className="flex items-center justify-between rounded border border-gray-100 px-2 py-1.5 text-sm">
                  <span>📎 {a.filename}{a.descricao ? ` — ${a.descricao}` : ""}</span>
                  <span className="text-xs text-gray-400">{fmtDate(a.criado_em)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </>
  );
}