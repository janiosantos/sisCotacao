// pages/produtos/status-cadastro.tsx — status de cadastro do produto (MDM-006).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Select } from "../../ui/ui";

const STATUS_LABEL: Record<string, string> = {
  rascunho: "Rascunho",
  em_revisao: "Em revisão",
  publicado: "Publicado",
  bloqueado: "Bloqueado",
};

export function StatusCadastro({ produtoId, inicial }: { produtoId: number; inicial?: string | null }) {
  const [status, setStatus] = useState<string>(inicial || "rascunho");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    setStatus(inicial || "rascunho");
  }, [inicial]);

  const alterar = async (novo: string) => {
    if (novo === status) return;
    setSalvando(true);
    try {
      const r = await api.alterarStatusCadastro(produtoId, novo);
      setStatus(r.status_cadastro);
      toast(`Status: ${STATUS_LABEL[r.status_cadastro] || r.status_cadastro}`, "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <label className="flex items-center gap-2 text-sm text-gray-600">
      <span className="text-xs font-medium uppercase text-gray-500">Status</span>
      <Select value={status} onChange={(e) => void alterar(e.target.value)} disabled={salvando} className="w-40">
        {Object.entries(STATUS_LABEL).map(([k, l]) => (
          <option key={k} value={k}>
            {l}
          </option>
        ))}
      </Select>
    </label>
  );
}