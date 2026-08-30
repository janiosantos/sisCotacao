// pages/configuracoes/loja.tsx - módulo Configurações (Loja).

import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button } from "../../ui/ui";

export function Loja() {
  const [cfg, setCfg] = useState<{
    bloquear_venda_sem_estoque: boolean;
    bloquear_venda_sem_credito: boolean;
    bloquear_venda_com_atraso: boolean;
  } | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    void api
      .lojaConfig()
      .then((c) =>
        setCfg({
          bloquear_venda_sem_estoque: !!c.bloquear_venda_sem_estoque,
          bloquear_venda_sem_credito: !!c.bloquear_venda_sem_credito,
          bloquear_venda_com_atraso: !!c.bloquear_venda_com_atraso,
        })
      )
      .catch(() => {});
  }, []);

  const salvar = async () => {
    if (!cfg) return;
    setSalvando(true);
    try {
      await api.setLojaConfig(cfg);
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
      {cfg == null ? (
        <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={cfg.bloquear_venda_sem_estoque}
              onChange={(e) => setCfg({ ...cfg, bloquear_venda_sem_estoque: e.target.checked })}
            />
            Bloquear venda sem estoque
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={cfg.bloquear_venda_sem_credito}
              onChange={(e) => setCfg({ ...cfg, bloquear_venda_sem_credito: e.target.checked })}
            />
            Bloquear venda acima do limite de crédito do cliente
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={cfg.bloquear_venda_com_atraso}
              onChange={(e) => setCfg({ ...cfg, bloquear_venda_com_atraso: e.target.checked })}
            />
            Bloquear venda para cliente com conta em atraso
          </label>
          <Button variant="primary" onClick={() => void salvar()} disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar"}
          </Button>
        </div>
      )}
    </section>
  );
}


