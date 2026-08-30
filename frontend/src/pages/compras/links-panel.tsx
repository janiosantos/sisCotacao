// pages/compras/links-panel.tsx — links de convite disparados por fornecedor (Etapa 2).
import { useState } from "react";
import { api, type Invite } from "../../api/client";
import { copiarTexto, toast } from "../../ui/dom";
import { Button } from "../../ui/ui";

export function LinksPanel({ cotacaoId, invites, onVoltar, onComparar }: { cotacaoId: number | null; invites: Invite[]; onVoltar: () => void; onComparar: () => void }) {
  const [lembrando, setLembrando] = useState<number | null>(null);

  const lembrar = async (inv: Invite) => {
    if (!cotacaoId) return;
    setLembrando(inv.fornecedor_id);
    try {
      const r = await api.lembrarFornecedor(cotacaoId, inv.fornecedor_id);
      if (r.whatsapp_url) {
        window.open(r.whatsapp_url, "_blank", "noopener,noreferrer");
        toast("Lembrete aberto no WhatsApp");
      } else if (r.mailto_url) {
        window.location.href = r.mailto_url;
        toast("Lembrete aberto no e-mail");
      } else {
        const ok = await copiarTexto(r.link);
        toast(ok ? "Sem contato — link copiado!" : "Não foi possível copiar", ok ? "" : "error");
      }
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setLembrando(null);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900">Cotações disparadas! Envie para cada fornecedor</h3>
      <p className="mb-3 text-sm text-gray-500">Toque no WhatsApp (verde) para abrir a conversa pronta, ou copie o link. O botão "Lembrar" reenvia a mensagem para quem ainda não respondeu.</p>
      <div className="space-y-2">
        {invites.map((inv) => (
          <div key={inv.fornecedor_id} className="flex flex-wrap items-center gap-3 rounded-md border border-gray-100 p-2">
            <div className="flex-1">
              <b className="text-sm">{inv.nome}</b>
              <span className="ml-2 text-xs text-gray-400">{inv.status === "respondido" ? "✓ respondeu" : "pendente"}</span>
              {inv.data_limite_retorno ? <span className="ml-2 text-xs text-gray-400">retorno até {inv.data_limite_retorno}</span> : null}
            </div>
            <div className="flex gap-2">
              {inv.whatsapp_url ? (
                <a className="rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700" target="_blank" rel="noopener noreferrer" href={inv.whatsapp_url}>
                  WhatsApp
                </a>
              ) : null}
              {inv.mailto_url ? (
                <a className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50" href={inv.mailto_url}>
                  E-mail
                </a>
              ) : null}
              <Button size="sm" onClick={() => void copiarTexto(inv.link).then((ok) => toast(ok ? "Link copiado!" : "Não foi possível copiar", ok ? "" : "error"))}>
                Copiar link
              </Button>
              {inv.status !== "respondido" ? (
                <Button size="sm" variant="secondary" onClick={() => void lembrar(inv)} disabled={lembrando === inv.fornecedor_id}>
                  {lembrando === inv.fornecedor_id ? "…" : "🔔 Lembrar"}
                </Button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-between">
        <Button onClick={onVoltar}>← Editar lista</Button>
        <Button variant="primary" onClick={onComparar}>
          Ir para Comparação ➔
        </Button>
      </div>
    </div>
  );
}