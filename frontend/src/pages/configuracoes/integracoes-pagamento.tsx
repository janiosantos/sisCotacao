// pages/configuracoes/integracoes-pagamento.tsx - módulo Configurações (IntegracoesPagamento).

import { useEffect, useState } from "react";
import { api, type PaymentProviderConfig } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Field, Input, Select } from "../../ui/ui";

export function IntegracoesPagamento() {
  const [providers, setProviders] = useState<{ id: number; codigo: string; nome: string }[]>([]);
  const [configs, setConfigs] = useState<PaymentProviderConfig[]>([]);
  const [editando, setEditando] = useState<PaymentProviderConfig | null>(null);
  const [form, setForm] = useState({
    provider_id: "",
    operacao: "boleto",
    ambiente: "sandbox",
    client_id: "",
    client_secret: "",
    access_token: "",
    api_key: "",
    chave_pix: "",
    conta: "",
    webhook_secret: "",
    prioridade: "10",
    ativo: true,
  });
  const [salvando, setSalvando] = useState(false);

  const carregar = async () => {
    try {
      const r = await api.listarPaymentProviders();
      setProviders(r.providers);
      setConfigs(r.configs);
    } catch {
      toast("Não foi possível ler as integrações", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrirNovo = () => {
    setEditando(null);
    setForm({
      provider_id: providers[0] ? String(providers[0].id) : "",
      operacao: "boleto",
      ambiente: "sandbox",
      client_id: "",
      client_secret: "",
      access_token: "",
      api_key: "",
      chave_pix: "",
      conta: "",
      webhook_secret: "",
      prioridade: "10",
      ativo: true,
    });
  };

  const abrir = (c: PaymentProviderConfig) => {
    setEditando(c);
    setForm({
      provider_id: String(c.provider_id),
      operacao: c.operacao,
      ambiente: c.ambiente,
      client_id: c.client_id || "",
      client_secret: c.client_secret || "",
      access_token: c.access_token || "",
      api_key: c.api_key || "",
      chave_pix: c.chave_pix || "",
      conta: c.conta || "",
      webhook_secret: c.webhook_secret || "",
      prioridade: String(c.prioridade ?? 10),
      ativo: !!c.ativo,
    });
  };

  const salvar = async () => {
    if (!form.provider_id) {
      toast("Escolha o provedor", "error");
      return;
    }
    setSalvando(true);
    try {
      await api.salvarPaymentProviderConfig({ ...form, ativo: form.ativo ? 1 : 0 });
      toast("Configuração salva", "success");
      setEditando(null);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const provNome = (id: number) => providers.find((p) => p.id === id)?.nome || String(id);

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Integrações de pagamento</h2>
          <p className="text-sm text-gray-500">
            Boleto e PIX nas contas a receber. A prioridade define o provedor usado (menor = preferido).
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={abrirNovo}>
          + Configurar
        </Button>
      </div>

      {configs.length === 0 ? (
        <p className="py-6 text-center text-sm text-gray-400">
          Nenhuma integração configurada. Configure Asaas ou Mercado Pago (sandbox) para emitir boleto/PIX.
        </p>
      ) : (
        <div className="space-y-2">
          {configs.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-md border border-gray-100 px-3 py-2 text-sm">
              <div className="flex items-center gap-3">
                <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativo" : "Inativo"}</Badge>
                <span className="font-medium">{provNome(c.provider_id)}</span>
                <span className="text-xs text-gray-400">
                  {c.operacao} · {c.ambiente} · prioridade {c.prioridade}
                </span>
                <Badge tone={c.credencial_configurada ? "green" : "red"}>
                  {c.credencial_configurada ? "credenciais ✓" : "credenciais ✗"}
                </Badge>
                <Badge tone={c.webhook_configurado ? "green" : "red"}>
                  {c.webhook_configurado ? "webhook ✓" : "webhook ✗"}
                </Badge>
              </div>
              <Button size="sm" variant="ghost" onClick={() => abrir(c)}>
                Editar
              </Button>
            </div>
          ))}
        </div>
      )}

      {editando !== null || form.provider_id !== "" ? (
        <div className="mt-4 rounded-md border border-dashed border-gray-300 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Provedor">
              <Select value={form.provider_id} onChange={(e) => setForm({ ...form, provider_id: e.target.value })}>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nome}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Operação">
                <Select value={form.operacao} onChange={(e) => setForm({ ...form, operacao: e.target.value })}>
                  <option value="boleto">Boleto</option>
                  <option value="pix">PIX</option>
                </Select>
              </Field>
              <Field label="Ambiente">
                <Select value={form.ambiente} onChange={(e) => setForm({ ...form, ambiente: e.target.value })}>
                  <option value="sandbox">Sandbox</option>
                  <option value="producao">Produção</option>
                </Select>
              </Field>
            </div>
            <Field label="API Key / Access Token">
              <Input value={form.api_key || form.access_token} onChange={(e) => {
                setForm({ ...form, api_key: e.target.value, access_token: e.target.value });
              }} placeholder={editando?.credencial_configurada ? "•••••••• (já configurado — deixe vazio p/ manter)" : "Asaas: API Key · Mercado Pago: Access Token"} />
            </Field>
            <Field label="Chave PIX">
              <Input value={form.chave_pix} onChange={(e) => setForm({ ...form, chave_pix: e.target.value })} placeholder="Chave PIX (e-mail, CPF, CNPJ, telefone, aleatória)" />
            </Field>
            <Field label="Segredo do Webhook (token/assinatura)">
              <Input value={form.webhook_secret} onChange={(e) => setForm({ ...form, webhook_secret: e.target.value })} placeholder={editando?.webhook_configurado ? "•••••••• (já configurado — deixe vazio p/ manter)" : "Asaas authToken · MP secret · EfiPay token"} />
              <p className="mt-1 text-xs text-gray-400">
                Valida a autenticidade das notificações. Asaas: header asaas-access-token · Mercado Pago: x-signature · EfiPay: ?token=
              </p>
            </Field>
            <Field label="Conta / identificador">
              <Input value={form.conta} onChange={(e) => setForm({ ...form, conta: e.target.value })} placeholder="Conta no provedor (opcional)" />
            </Field>
            <Field label="Prioridade (menor = preferido)">
              <Input type="number" min={1} value={form.prioridade} onChange={(e) => setForm({ ...form, prioridade: e.target.value })} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} />
              Ativo
            </label>
          </div>
          <div className="mt-3 flex gap-2">
            <Button onClick={() => setForm({ ...form, provider_id: "" })}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()} disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

