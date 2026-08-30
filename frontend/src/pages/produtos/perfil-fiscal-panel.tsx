// pages/produtos/perfil-fiscal-panel.tsx — perfil fiscal efetivo do produto
// (NCM/CEST/origem/regime ST, herança vs override, validações inline e busca NCM).
import { useEffect, useState } from "react";
import { api, type PerfilFiscalEfetivo, type ProdutoCadastro } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button } from "../../ui/ui";

export function PerfilFiscalPanel({ produto }: { produto: ProdutoCadastro | null }) {
  const [efetivo, setEfetivo] = useState<PerfilFiscalEfetivo | null>(null);
  const [ncmBusca, setNcmBusca] = useState("");
  const [ncmResultados, setNcmResultados] = useState<{ codigo: string; descricao: string }[]>([]);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!produto) return;
    api.perfilFiscalEfetivo(produto.id).then(setEfetivo).catch(() => toast("Erro ao ler perfil fiscal", "error"));
  }, [produto]);

  const buscarNcm = async () => {
    if (!ncmBusca.trim()) return;
    try {
      setNcmResultados(await api.buscarNcm(ncmBusca.trim()));
    } catch (e) {
      toast("Erro na busca de NCM: " + (e as Error).message, "error");
    }
  };

  const salvar = async () => {
    if (!produto || !efetivo) return;
    setSalvando(true);
    try {
      const salvo = await api.perfilFiscalSalvar(produto.id, efetivo.efetivo);
      setEfetivo({ ...efetivo, variante: salvo, efetivo: salvo });
      toast("Perfil fiscal salvo", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  if (!produto) {
    return <p className="py-8 text-center text-sm text-gray-400">Salve o produto para classificar o perfil fiscal.</p>;
  }

  const campo = "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm";

  const ncmRegex = /^\d{4}(\.\d{2})?(\.\d{2})?$/;
  const precoOk = Number(produto.preco) > 0;
  const marcaOk = !!(produto.marca || "").trim();
  const ncmOk = !!efetivo && ncmRegex.test((efetivo.efetivo.ncm || "").trim());

  const campoErro = "border-red-400 bg-red-50 focus:border-red-500";
  const campoHerdado = (campoOverride: boolean) => (campoOverride ? "border-amber-400 bg-amber-50" : "border-gray-300");

  const badgeHerdado = (override: boolean) =>
    override ? (
      <Badge tone="amber">Override</Badge>
    ) : (
      <Badge tone="gray">Padrão</Badge>
    );

  return (
    <div className="max-w-xl space-y-4">
      {!efetivo ? (
        <p className="py-4 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <>
          {/* Validações inline do cadastro (marca, NCM, preço) */}
          <div className="rounded-md border border-gray-200 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Validações do cadastro</p>
            <ul className="space-y-1 text-xs">
              <li className={marcaOk ? "text-green-700" : "text-red-600"}>
                {marcaOk ? "✔" : "✘"} Marca do produto preenchida ({produto.marca || "—"})
              </li>
              <li className={precoOk ? "text-green-700" : "text-red-600"}>
                {precoOk ? "✔" : "✘"} Preço do produto &gt; 0 ({produto.preco != null ? fmtMoney(Number(produto.preco)) : "—"})
              </li>
              <li className={ncmOk ? "text-green-700" : "text-red-600"}>
                {ncmOk ? "✔" : "✘"} Formato NCM válido (ex.: 8544.42.00) — atual: {efetivo.efetivo.ncm || "vazio"}
              </li>
            </ul>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs uppercase text-gray-400">NCM {badgeHerdado(efetivo.override_campos.ncm)}</label>
              <input
                className={`${campo} ${ncmOk ? campoHerdado(efetivo.override_campos.ncm) : campoErro}`}
                value={efetivo.efetivo.ncm}
                onChange={(e) => setEfetivo({ ...efetivo, efetivo: { ...efetivo.efetivo, ncm: e.target.value } })}
                placeholder="ex.: 8544.42.00"
              />
              {!ncmOk && <p className="mt-1 text-[11px] text-red-500">Formato inválido — use 4 ou 8 dígitos (ex.: 8544 ou 8544.42.00).</p>}
            </div>
            <div>
              <label className="text-xs uppercase text-gray-400">CEST {badgeHerdado(efetivo.override_campos.cest)}</label>
              <input className={`${campo} ${campoHerdado(efetivo.override_campos.cest)}`} value={efetivo.efetivo.cest} onChange={(e) => setEfetivo({ ...efetivo, efetivo: { ...efetivo.efetivo, cest: e.target.value } })} placeholder="opcional" />
              <p className="mt-1 text-[11px] text-gray-400">Fios/cabos uso construção (8544): <b>12.007.00</b> — Anexo VII Cap.12 item 7.0 (Conf. Consulta SEF/MG 105/2021).</p>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-400">Origem da mercadoria {badgeHerdado(efetivo.override_campos.origem)}</label>
              <select className={`${campo} ${campoHerdado(efetivo.override_campos.origem)}`} value={efetivo.efetivo.origem} onChange={(e) => setEfetivo({ ...efetivo, efetivo: { ...efetivo.efetivo, origem: Number(e.target.value) } })}>
                <option value={0}>0 — Nacional (exceto 3, 4, 5 e 8)</option>
                <option value={1}>1 — Estrangeira — importação direta</option>
                <option value={2}>2 — Estrangeira — adquirida no mercado interno</option>
                <option value={3}>3 — Nacional, conteúdo importação &gt; 40%</option>
                <option value={4}>4 — Nacional, processos produtivos básicos</option>
                <option value={5}>5 — Nacional, processo produtivo básico</option>
                <option value={8}>8 — Nacional, conteúdo importação ≤ 40%</option>
              </select>
              <p className="mt-1 text-[11px] text-gray-400">Vem das NFs de entrada dos fornecedores (não é consulta legal).</p>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-400">Enquadramento ST (regime_st) {badgeHerdado(efetivo.override_campos.regime_st)}</label>
              <input className={`${campo} ${campoHerdado(efetivo.override_campos.regime_st)}`} value={efetivo.efetivo.regime_st} onChange={(e) => setEfetivo({ ...efetivo, efetivo: { ...efetivo.efetivo, regime_st: e.target.value } })} placeholder="opcional" />
              <p className="mt-1 text-[11px] text-gray-400">Ex.: <code>substituido_ja_retido</code> quando a entrada reteve ICMS-MG.</p>
            </div>
          </div>

          {efetivo.produto ? (
            <p className="rounded-md bg-gray-50 px-3 py-2 text-[11px] text-gray-500">
              Perfil padrão do produto: NCM <b>{efetivo.produto.ncm || "—"}</b> · CEST{" "}
              <b>{efetivo.produto.cest || "—"}</b> · Origem <b>{efetivo.produto.origem ?? 0}</b> · Regime ST{" "}
              <b>{efetivo.produto.regime_st || "—"}</b>. Edite um campo para sobrescrever (override).
            </p>
          ) : (
            <p className="rounded-md bg-gray-50 px-3 py-2 text-[11px] text-gray-500">
              Sem perfil padrão no produto — os valores preenchidos aqui valem somente para este produto.
            </p>
          )}

          <div className="rounded-md border border-gray-200 p-3">
            <p className="mb-2 text-xs uppercase text-gray-400">Buscar NCM versionado (fonte oficial)</p>
            <div className="flex gap-2">
              <input
                className={campo}
                value={ncmBusca}
                onChange={(e) => setNcmBusca(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void buscarNcm()}
                placeholder="código ou termo da descrição"
              />
              <Button onClick={() => void buscarNcm()}>Buscar</Button>
            </div>
            {ncmResultados.length > 0 && (
              <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-sm">
                {ncmResultados.map((n) => (
                  <li key={n.codigo}>
                    <button
                      type="button"
                      className="text-left hover:underline"
                      onClick={() =>
                        setEfetivo((prev: PerfilFiscalEfetivo | null) =>
                          prev ? { ...prev, efetivo: { ...prev.efetivo, ncm: n.codigo } } : prev,
                        )
                      }
                    >
                      <span className="font-mono">{n.codigo}</span> — {n.descricao}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-[11px] text-gray-400">NCM não encontrado? Registre com fonte oficial via POST /api/fiscal/ncm — nunca inventar código.</p>
          </div>

          <div className="flex justify-end">
            <Button variant="primary" disabled={salvando} onClick={() => void salvar()}>
              {salvando ? "Salvando…" : "Salvar perfil fiscal"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}