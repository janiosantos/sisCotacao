// pages/configuracoes.tsx — parâmetros do sistema.

import { useEffect, useState } from "react";
import { api, type ConfigImpressao, type FeatureFlag } from "../api/client";
import { toast } from "../ui/dom";
import { Button, Field, Input, PageHeader, Select } from "../ui/ui";

export default function Configuracoes() {
  return (
    <div>
      <PageHeader title="Configurações" subtitle="Parâmetros do sistema." />
      <div className="max-w-2xl space-y-8">
        <Flags />
        <Impressora />
        <Loja />
      </div>
    </div>
  );
}

function Flags() {
  const [items, setItems] = useState<FeatureFlag[] | null>(null);
  const [salvando, setSalvando] = useState<string | null>(null);

  useEffect(() => {
    api
      .listarFlags()
      .then((r) => setItems(r.flags))
      .catch(() => toast("Não foi possível ler as feature flags", "error"));
  }, []);

  const alternar = async (f: FeatureFlag) => {
    setSalvando(f.nome);
    try {
      await api.definirFlag(f.nome, !f.ativo);
      setItems(
        (prev) =>
          prev?.map((x) => (x.nome === f.nome ? { ...x, ativo: !f.ativo } : x)) ?? [],
      );
      toast(`Flag ${f.nome} ${!f.ativo ? "ativada" : "desativada"}`, "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(null);
    }
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-1 text-base font-semibold">Feature flags</h2>
      <p className="mb-4 text-sm text-gray-500">
        Alterna comportamentos em runtime — rollback sem deploy.
      </p>
      {!items ? (
        <p className="py-4 text-center text-sm text-gray-400">Carregando…</p>
      ) : items.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-400">
          Nenhuma flag registrada. Registre em `catalog_server/flags.py`.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((f) => (
            <label key={f.nome} className="flex items-start gap-3 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={f.ativo}
                disabled={salvando === f.nome}
                onChange={() => void alternar(f)}
                className="mt-1"
              />
              <span>
                <span className="font-mono font-semibold text-gray-800">{f.nome}</span>
                {f.descricao && <span className="block text-xs text-gray-500">{f.descricao}</span>}
              </span>
            </label>
          ))}
        </div>
      )}
    </section>
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
        driver: cfg.driver || "escpos_tcp",
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
      <h2 className="mb-1 text-base font-semibold text-gray-900">Retaguarda de impressão</h2>
      <p className="mb-4 text-sm text-gray-500">O cupom é entregue ao driver escolhido abaixo, sem diálogo de impressora.</p>

      {!cfg ? (
        <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <div className="space-y-4">
          <Field label="Tipo de impressora (driver)">
            <Select value={cfg.driver || "escpos_tcp"} onChange={(e) => setCfg({ ...cfg, driver: e.target.value })}>
              <option value="escpos_tcp">ESC/POS via rede (TCP) — porta 9100</option>
              <option value="arquivo">Arquivo (grava o cupom em binário, para teste)</option>
            </Select>
          </Field>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Host">
              <Input value={cfg.host} onChange={(e) => setCfg({ ...cfg, host: e.target.value })} disabled={(cfg.driver || "escpos_tcp") !== "escpos_tcp"} />
            </Field>
            <Field label="Porta">
              <Input type="number" min={1} max={65535} value={cfg.porta} onChange={(e) => setCfg({ ...cfg, porta: parseInt(e.target.value, 10) || 0 })} disabled={(cfg.driver || "escpos_tcp") !== "escpos_tcp"} />
            </Field>
            <Field label="Papel (mm)">
              <Select value={String(cfg.papel_mm)} onChange={(e) => setCfg({ ...cfg, papel_mm: parseInt(e.target.value, 10) })}>
                <option value="80">80 mm</option>
                <option value="58">58 mm</option>
              </Select>
            </Field>
          </div>
          <p className="text-xs text-gray-400">
            Em Docker, o host <code>127.0.0.1</code> é enviado automaticamente para a máquina do emulador
            (<code>host.docker.internal</code>) — a impressora/emulador deve estar rodando no computador hospedeiro.
          </p>
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
