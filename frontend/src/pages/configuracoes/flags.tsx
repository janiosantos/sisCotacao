// pages/configuracoes/flags.tsx - módulo Configurações (Flags).

import { useEffect, useState } from "react";
import { api, type FeatureFlag } from "../../api/client";
import { toast } from "../../ui/dom";

export function Flags() {
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


