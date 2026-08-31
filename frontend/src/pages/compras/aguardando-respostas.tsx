// pages/compras/aguardando-respostas.tsx — cotação aberta aguardando fornecedores (Etapa 3).
import { useEffect, useState } from "react";
import { api, type Invite, type MatrizComparacao } from "../../api/client";
import { copiarTexto, toast } from "../../ui/dom";
import { Badge, Button, Card, StatCard } from "../../ui/ui";

export function AguardandoRespostas({
  cotacaoId,
  m,
  onAtualizar,
}: {
  cotacaoId: number | null;
  m: MatrizComparacao;
  onAtualizar: () => void;
}) {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [quantidades, setQuantidades] = useState<Record<number, string>>(() => {
    const init: Record<number, string> = {};
    for (const it of m.itens) init[it.cotacao_item_id] = String(it.quantidade);
    return init;
  });
  const [salvando, setSalvando] = useState<number | null>(null);
  const [lembrando, setLembrando] = useState<number | null>(null);

  useEffect(() => {
    if (!cotacaoId) return;
    void api
      .convitesCotacao(cotacaoId)
      .then(setInvites)
      .catch(() => setInvites([]));
  }, [cotacaoId]);

  const salvarQtd = async (itemId: number) => {
    if (!cotacaoId) return;
    setSalvando(itemId);
    try {
      await api.atualizarItem(cotacaoId, itemId, { quantidade: Number(quantidades[itemId]) || 1 });
      toast("Quantidade atualizada", "success");
      onAtualizar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(null);
    }
  };

  // Fonte primária: fornecedores da matriz (nunca vazio se convidados).
  // Os invites (quando carregados) trazem os links prontos.
  const fornecedores = m.fornecedores.map((f) => {
    const inv = invites.find((i) => i.fornecedor_id === f.fornecedor_id);
    return { ...f, link: inv?.link, whatsapp_url: inv?.whatsapp_url || "" };
  });
  const respondidos = fornecedores.filter((f) => f.status === "respondido").length;
  const pendentes = fornecedores.length - respondidos;

  const obterLink = async (fid: number): Promise<string | null> => {
    if (!cotacaoId) return null;
    const inv = invites.find((i) => i.fornecedor_id === fid);
    if (inv?.link) return inv.link;
    const r = await api.lembrarFornecedor(cotacaoId, fid);
    setInvites((cur) => {
      const idx = cur.findIndex((i) => i.fornecedor_id === fid);
      if (idx >= 0) {
        const next = [...cur];
        next[idx] = r;
        return next;
      }
      return [...cur, r];
    });
    return r.link;
  };

  const copiarLink = async (fid: number) => {
    try {
      const link = await obterLink(fid);
      if (link) {
        const ok = await copiarTexto(link);
        toast(ok ? "Link copiado!" : "Não foi possível copiar", ok ? "" : "error");
      } else {
        toast("Sem link disponível para este fornecedor.", "error");
      }
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const lembrar = async (fid: number, nome: string) => {
    if (!cotacaoId) return;
    setLembrando(fid);
    try {
      const r = await api.lembrarFornecedor(cotacaoId, fid);
      setInvites((cur) => {
        const idx = cur.findIndex((i) => i.fornecedor_id === fid);
        if (idx >= 0) {
          const next = [...cur];
          next[idx] = r;
          return next;
        }
        return [...cur, r];
      });
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
      toast(`Não foi possível gerar o convite de ${nome}: ` + (e as Error).message, "error");
    } finally {
      setLembrando(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard label="Respostas" value={`${respondidos}/${fornecedores.length}`} sub="fornecedores responderam" tone={respondidos ? "success" : "default"} />
        <StatCard label="Pendentes" value={String(pendentes)} sub="convites ainda abertos" tone={pendentes ? "highlight" : "default"} />
        <StatCard label="Itens" value={String(m.itens.length)} sub="podem ser ajustados antes do fechamento" />
      </div>

      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Cotação {m.cotacao.numero} — aguardando respostas</h3>
            <p className="text-sm text-gray-500">
              Você pode atualizar quantidades enquanto os convites continuam abertos.
            </p>
          </div>
          <Button variant="primary" onClick={onAtualizar}>
            ↻ Atualizar respostas
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[680px] w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-3 py-2">Produto</th>
                <th className="px-3 py-2">SKU</th>
                <th className="px-3 py-2">Quantidade</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {m.itens.map((it) => (
                <tr key={it.cotacao_item_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{it.name}</td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-400">{it.sku || "—"}</td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min={1}
                      aria-label={`Quantidade de ${it.name}`}
                      value={quantidades[it.cotacao_item_id] ?? it.quantidade}
                      onChange={(e) => setQuantidades({ ...quantidades, [it.cotacao_item_id]: e.target.value })}
                      className="w-24 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button size="sm" onClick={() => void salvarQtd(it.cotacao_item_id)} disabled={salvando === it.cotacao_item_id}>
                      {salvando === it.cotacao_item_id ? "…" : "Salvar"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="p-4">
        <div className="mb-3">
          <h4 className="text-sm font-semibold text-gray-900">Enviar ou reenviar convite</h4>
          <p className="mt-1 text-sm text-gray-500">Use WhatsApp quando houver contato. Caso contrário, copie o link seguro do fornecedor.</p>
        </div>
        {fornecedores.length === 0 ? (
          <p className="text-sm text-gray-400">Nenhum fornecedor convidado nesta cotação.</p>
        ) : (
          <div className="space-y-2">
            {fornecedores.map((f) => (
              <div key={f.fornecedor_id} className="flex flex-wrap items-center gap-3 rounded-md border border-gray-100 p-2">
                <div className="flex-1">
                  <b className="text-sm">{f.nome}</b>
                  <span className="ml-2"><Badge tone={f.status === "respondido" ? "green" : "amber"}>{f.status === "respondido" ? "Respondeu" : "Pendente"}</Badge></span>
                  {f.data_limite_retorno ? <span className="ml-2 text-xs text-gray-400">retorno até {f.data_limite_retorno}</span> : null}
                </div>
                <div className="flex gap-2">
                  {f.whatsapp_url ? (
                    <a className="rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700" target="_blank" rel="noopener noreferrer" href={f.whatsapp_url}>
                      WhatsApp
                    </a>
                  ) : null}
                  <Button size="sm" onClick={() => void copiarLink(f.fornecedor_id)}>
                      Copiar link
                  </Button>
                  {f.status !== "respondido" ? (
                    <Button size="sm" variant="secondary" onClick={() => void lembrar(f.fornecedor_id, f.nome)} disabled={lembrando === f.fornecedor_id}>
                      {lembrando === f.fornecedor_id ? "…" : "Lembrar fornecedor"}
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
