// pages/configuracoes.tsx — parâmetros do sistema.

import { useEffect, useState } from "react";
import { api, type ConfigImpressao } from "../api/client";
import { toast } from "../ui/dom";
import { Button, Field, Input, PageHeader, Select } from "../ui/ui";

export default function Configuracoes() {
  return (
    <div>
      <PageHeader title="Configurações" subtitle="Parâmetros do sistema." />
      <div className="max-w-2xl space-y-8">
        <Impressora />
        <Loja />
      </div>
    </div>
  );
}

function Impressora() {
  const [cfg, setCfg] = useState<ConfigImpressao | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [testando, setTestando] = useState(false);

  useEffect(() => {
    void api
      .getConfigImpressao()
      .then(setCfg)
      .catch(() => toast("Não foi possível ler a config da impressora", "error"));
  }, []);

  const salvar = async () => {
    if (!cfg) return;
    setSalvando(true);
    try {
      await api.setConfigImpressao({
        host: cfg.host.trim(),
        porta: cfg.porta,
        papel_mm: cfg.papel_mm,
        auto_impressao: cfg.auto_impressao,
      });
      toast("Config salva", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const testar = async () => {
    setTestando(true);
    try {
      await api.imprimirTeste();
      toast("Teste enviado para a impressora", "success");
    } catch (e) {
      toast("Teste falhou: " + (e as Error).message, "error");
    } finally {
      setTestando(false);
    }
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-1 text-base font-semibold text-gray-900">Retaguarda de impressão (ESC/POS)</h2>
      <p className="mb-4 text-sm text-gray-500">O cupom é enviado direto (ESC/POS) a esta impressora, sem diálogo.</p>

      {!cfg ? (
        <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Field label="Host">
              <Input value={cfg.host} onChange={(e) => setCfg({ ...cfg, host: e.target.value })} />
            </Field>
            <Field label="Porta">
              <Input type="number" min={1} max={65535} value={cfg.porta} onChange={(e) => setCfg({ ...cfg, porta: parseInt(e.target.value, 10) || 0 })} />
            </Field>
            <Field label="Papel (mm)">
              <Select value={String(cfg.papel_mm)} onChange={(e) => setCfg({ ...cfg, papel_mm: parseInt(e.target.value, 10) })}>
                <option value="80">80 mm</option>
                <option value="58">58 mm</option>
              </Select>
            </Field>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={!!cfg.auto_impressao}
              onChange={(e) => setCfg({ ...cfg, auto_impressao: e.target.checked ? 1 : 0 })}
            />
            Imprimir automaticamente ao salvar
          </label>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => void testar()} disabled={testando}>
              {testando ? "Enviando…" : "Testar"}
            </Button>
            <Button variant="primary" onClick={() => void salvar()} disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

function Loja() {
  const [bloquear, setBloquear] = useState<boolean | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    void api
      .lojaConfig()
      .then((c) => setBloquear(!!c.bloquear_venda_sem_estoque))
      .catch(() => {});
  }, []);

  const salvar = async () => {
    if (bloquear == null) return;
    setSalvando(true);
    try {
      await api.setLojaConfig({ bloquear_venda_sem_estoque: bloquear });
      toast("Configuração salva", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-4 text-base font-semibold text-gray-900">Loja</h2>
      {bloquear == null ? (
        <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <div className="space-y-4">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={bloquear} onChange={(e) => setBloquear(e.target.checked)} />
            Bloquear venda sem estoque
          </label>
          <Button variant="primary" onClick={() => void salvar()} disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar"}
          </Button>
        </div>
      )}
    </section>
  );
}
