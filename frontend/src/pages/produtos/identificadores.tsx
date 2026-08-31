// pages/produtos/identificadores.tsx — códigos múltiplos por produto (MDM-003).
import { useEffect, useState } from "react";
import { api, type ProdutoIdentificador } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Loading, Select } from "../../ui/ui";

const TIPO_LABEL: Record<string, string> = {
  ean: "EAN (código de barras)",
  gtin: "GTIN",
  codigo_interno: "Código interno",
  fabricante: "Código do fabricante",
  fornecedor: "Código do fornecedor",
  embalagem: "Embalagem",
};

export function Identificadores({ produtoId }: { produtoId: number }) {
  const [rows, setRows] = useState<ProdutoIdentificador[] | null>(null);
  const [tipo, setTipo] = useState("ean");
  const [valor, setValor] = useState("");
  const [embalagem, setEmbalagem] = useState("");
  const [salvando, setSalvando] = useState(false);

  const carregar = async () => {
    setRows(null);
    try {
      setRows((await api.listarIdentificadores(produtoId)).identificadores);
    } catch (e) {
      toast("Erro ao carregar códigos: " + (e as Error).message, "error");
      setRows([]);
    }
  };

  useEffect(() => {
    void carregar();
  }, [produtoId]);

  const salvar = async () => {
    if (!valor.trim()) {
      toast("Informe o valor do código", "error");
      return;
    }
    setSalvando(true);
    try {
      await api.salvarIdentificador(produtoId, {
        tipo,
        valor: valor.trim(),
        embalagem: tipo === "embalagem" ? embalagem.trim() || null : null,
      });
      toast("Código salvo", "success");
      setValor("");
      setEmbalagem("");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (id: number) => {
    try {
      await api.excluirIdentificador(produtoId, id);
      toast("Código removido", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  if (rows === null) return <Loading message="Carregando códigos…" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Permite vários códigos por produto (EAN/GTIN, código interno, do fabricante, do fornecedor e de embalagem).
        A busca exata por qualquer código ativo encontra o produto antes da busca textual.
      </p>

      {rows.length === 0 ? (
        <p className="rounded-md border border-dashed border-gray-300 bg-white py-6 text-center text-sm text-gray-400">
          Nenhum código cadastrado.
        </p>
      ) : (
        <div className="space-y-2">
          {rows.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
              <span>
                <span className="font-medium">{TIPO_LABEL[c.tipo] || c.tipo}</span>
                {c.embalagem ? <span className="ml-1 font-mono text-xs text-gray-500">({c.embalagem})</span> : null}
                <span className="ml-2 font-mono text-gray-700">{c.valor}</span>
              </span>
              <Button size="sm" variant="ghost" onClick={() => void excluir(c.id)}>
                ×
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-md border border-dashed border-gray-300 p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Novo código</div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Tipo">
            <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
              {Object.entries(TIPO_LABEL).map(([k, l]) => (
                <option key={k} value={k}>
                  {l}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={tipo === "embalagem" ? "Embalagem" : "Valor"}>
            <Input
              placeholder={tipo === "ean" || tipo === "gtin" ? "0000000000000" : "Ex.: INT-001"}
              maxLength={40}
              value={valor}
              onChange={(e) => setValor(e.target.value)}
            />
          </Field>
          {tipo === "embalagem" ? (
            <Field label="Valor">
              <Input maxLength={40} value={embalagem} onChange={(e) => setEmbalagem(e.target.value)} placeholder="Ex.: CX-12" />
            </Field>
          ) : null}
        </div>
        <div className="mt-3">
          <Button size="sm" variant="primary" onClick={() => void salvar()} disabled={salvando}>
            {salvando ? "Salvando…" : "+ Salvar código"}
          </Button>
        </div>
      </div>
    </div>
  );
}