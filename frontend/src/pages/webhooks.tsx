import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { Button, Select, Badge, Table, TBody, THead, Cell, EmptyRow } from "../ui/ui";
import { toast } from "../ui/dom";

interface WebhookLogItem {
  id: number;
  provider: string;
  evento: string | null;
  payment_id: string | null;
  status: string;
  http_status: number | null;
  assinatura_ok: boolean | null;
  ip: string | null;
  criado_em: string;
}

interface RechecagemResult {
  verificadas: number;
  pagas: number;
  ja_pagas: number;
  erros: string[];
  detalhes: { conta_id: number; payment_id: string; valor: number }[];
}

const STATUS_TONE: Record<string, "green" | "red" | "blue" | "gray" | "amber"> = {
  processado: "green",
  duplicado: "blue",
  ignorado: "gray",
  nao_autorizado: "red",
  nao_configurado: "red",
  payload_invalido: "red",
  caixa_pendente: "amber",
  erro: "red",
};

const STATUS_LABEL: Record<string, string> = {
  processado: "Processado",
  duplicado: "Duplicado",
  ignorado: "Ignorado",
  nao_autorizado: "Não autorizado",
  nao_configurado: "Não configurado",
  payload_invalido: "Payload inválido",
  caixa_pendente: "Caixa pendente",
  erro: "Erro",
};

export default function Webhooks() {
  const [items, setItems] = useState<WebhookLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [provider, setProvider] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [carregando, setCarregando] = useState(false);
  const [detalhe, setDetalhe] = useState<Record<string, unknown> | null>(null);
  const [rechecando, setRechecando] = useState(false);
  const [res, setRes] = useState<RechecagemResult | null>(null);
  const LIMIT = 30;

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const params: Record<string, string> = { limit: String(LIMIT), offset: String(offset) };
      if (provider) params.provider = provider;
      if (status) params.status = status;
      const r = await api.listarWebhookLogs(params);
      setItems(r.items);
      setTotal(r.total);
    } catch (e) {
      toast("Erro ao carregar logs: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  }, [provider, status, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const verDetalhe = async (id: number) => {
    try {
      setDetalhe(await api.detalheWebhookLog(id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const rechecagem = async () => {
    setRechecando(true);
    setRes(null);
    try {
      const r = await api.rechecagemWebhooks({ provider, limite: 100 });
      setRes(r);
      toast(`Rechecagem: ${r.verificadas} verificadas, ${r.pagas} pagas`, "success");
      await carregar();
    } catch (e) {
      toast("Erro na rechecagem: " + (e as Error).message, "error");
    } finally {
      setRechecando(false);
    }
  };

  const fmt = (d: string) => {
    try {
      return new Date(d).toLocaleString("pt-BR");
    } catch {
      return d;
    }
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Webhooks de pagamento</h2>
          <p className="text-sm text-gray-500">
            Notificações recebidas dos provedores (Asaas, Mercado Pago, EfiPay, Sicoob) e resultado de cada uma.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={provider} onChange={(e) => { setProvider(e.target.value); setOffset(0); }}>
            <option value="">Todos os provedores</option>
            <option value="asaas">Asaas</option>
            <option value="mercadopago">Mercado Pago</option>
            <option value="efipay">EfiPay</option>
            <option value="sicoob">Sicoob</option>
          </Select>
          <Select value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
            <option value="">Todos os status</option>
            <option value="processado">Processado</option>
            <option value="nao_autorizado">Não autorizado</option>
            <option value="duplicado">Duplicado</option>
            <option value="ignorado">Ignorado</option>
            <option value="erro">Erro</option>
          </Select>
          <Button size="sm" variant="secondary" onClick={() => void carregar()} disabled={carregando}>
            Atualizar
          </Button>
          <Button size="sm" variant="primary" onClick={() => void rechecagem()} disabled={rechecando}>
            {rechecando ? "Verificando…" : "Rechecagem em lote"}
          </Button>
        </div>
      </div>

      {res ? (
        <div className="mb-4 grid grid-cols-3 gap-3 rounded-md border border-gray-100 p-3 text-sm">
          <div><span className="text-gray-400">Verificadas:</span> <b>{res.verificadas}</b></div>
          <div><span className="text-gray-400">Pagas (baixadas):</span> <b className="text-green-600">{res.pagas}</b></div>
          <div><span className="text-gray-400">Erros:</span> <b className={res.erros.length ? "text-red-600" : ""}>{res.erros.length}</b></div>
          {res.erros.length ? (
            <div className="col-span-3 text-xs text-red-600">{res.erros.slice(0, 5).join(" · ")}</div>
          ) : null}
        </div>
      ) : null}

      <Table>
        <THead cols={["ID", "Data", "Provedor", "Evento", "Payment ID", "Status", "HTTP", "IP"]} />
        <TBody>
          {items.length === 0 ? (
            <EmptyRow colSpan={8} message={`Sem logs${carregando ? " (carregando…)" : ""}`} />
          ) : (
            items.map((it) => (
              <tr key={it.id} className="cursor-pointer hover:bg-gray-50" onClick={() => void verDetalhe(it.id)}>
                <Cell>{it.id}</Cell>
                <Cell>{fmt(it.criado_em)}</Cell>
                <Cell>{it.provider}</Cell>
                <Cell>{it.evento || "—"}</Cell>
                <Cell className="font-mono text-xs">{it.payment_id || "—"}</Cell>
                <Cell><Badge tone={STATUS_TONE[it.status] || "gray"}>{STATUS_LABEL[it.status] || it.status}</Badge></Cell>
                <Cell>{it.http_status ?? "—"}</Cell>
                <Cell>{it.ip || "—"}</Cell>
              </tr>
            ))
          )}
        </TBody>
      </Table>

      {total > LIMIT ? (
        <div className="mt-3 flex items-center justify-between text-sm">
          <Button size="sm" variant="ghost" disabled={offset <= 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← Anterior</Button>
          <span className="text-gray-500">{offset + 1}–{Math.min(offset + LIMIT, total)} de {total}</span>
          <Button size="sm" variant="ghost" disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>Próxima →</Button>
        </div>
      ) : null}

      {detalhe ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setDetalhe(null)}>
          <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-xl bg-white p-5" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Log #{String(detalhe.id)}</h3>
              <Button size="sm" variant="ghost" onClick={() => setDetalhe(null)}>Fechar</Button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>Provedor: <b>{String(detalhe.provider)}</b></div>
              <div>Status: <b>{String(detalhe.status)}</b></div>
              <div>Evento: <b>{String(detalhe.evento || "—")}</b></div>
              <div>Payment: <b className="font-mono">{String(detalhe.payment_id || "—")}</b></div>
              <div>HTTP: <b>{String(detalhe.http_status ?? "—")}</b></div>
              <div>Assinatura: <b>{detalhe.assinatura_ok === null ? "—" : detalhe.assinatura_ok === true ? "válida" : "inválida"}</b></div>
              <div>IP: <b>{String(detalhe.ip || "—")}</b></div>
              <div>Data: <b>{fmt(String(detalhe.criado_em))}</b></div>
            </div>
            {detalhe.erro ? <div className="mt-2 text-sm text-red-600">Erro: {String(detalhe.erro)}</div> : null}
            {detalhe.payload ? (
              <div className="mt-3">
                <div className="mb-1 text-xs font-medium text-gray-500">Payload (resumo)</div>
                <pre className="max-h-60 overflow-auto rounded bg-gray-50 p-2 text-xs whitespace-pre-wrap">{String(detalhe.payload)}</pre>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}