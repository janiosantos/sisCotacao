// pages/fiscal.tsx — fiscal (React + Tailwind).

import { useEffect, useRef, useState } from "react";
import {
  api,
  type BeneficioFiscalItem,
  type CestItem,
  type CfopCode,
  type Cliente,
  type CsosnItem,
  type CstCode,
  type FiscalConfigItem,
  type FiscalResultado,
  type HistoricoFiscalItem,
  type IbptItem,
  type NfeEntrada,
  type NfeSaida,
  type ProdutoResumo,
  type SugestaoIbpt,
} from "../api/client";
import { fmtDate, fmtDateTime, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import {
  Badge,
  Button,
  Cell,
  EmptyRow,
  Field,
  Input,
  Loading,
  Modal,
  PageHeader,
  Select,
  Table,
  TBody,
  THead,
} from "../ui/ui";

type Aba = "cfop" | "cst" | "cest" | "config" | "emitente" | "nfe" | "ibpt" | "sugestoes" | "simulador" | "historico";

const ORIGENS = [
  "Nacional (exceto 3 a 5 e 7 a 8)",
  "Estrangeira — importação direta",
  "Estrangeira — adquirida no mercado interno",
  "Nacional, conteúdo importação > 40%",
  "Nacional, produção conforme processo produtivo básico",
  "Nacional, conteúdo importação ≤ 40%",
  "Estrangeira — importação direta, sem similar nacional",
  "Estrangeira — mercado interno, sem similar nacional",
  "Nacional, conteúdo importação > 70%",
];

export default function Fiscal() {
  const [aba, setAba] = useState<Aba>("cfop");

  const TABS: { key: Aba; label: string }[] = [
    { key: "cfop", label: "CFOP" },
    { key: "cst", label: "CST" },
    { key: "cest", label: "CEST" },
    { key: "config", label: "Config. Fiscal" },
    { key: "emitente", label: "Emitente" },
    { key: "nfe", label: "NF-e" },
    { key: "ibpt", label: "IBPT" },
    { key: "sugestoes", label: "Sugestões NCM" },
    { key: "simulador", label: "Simulador" },
    { key: "historico", label: "Histórico" },
  ];

  return (
    <div>
      <PageHeader title="Fiscal" subtitle="CFOP, CST e configuração tributária por produto." />
      <div className="mb-5 flex gap-2 overflow-x-auto border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setAba(t.key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
              aba === t.key ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {aba === "cfop" && <Cfop />}
      {aba === "cst" && <Cst />}
      {aba === "cest" && <Cest />}
      {aba === "config" && <Config />}
      {aba === "emitente" && <EmitenteTab />}
      {aba === "nfe" && <Nfe />}
      {aba === "ibpt" && <Ibpt />}
      {aba === "sugestoes" && <Sugestoes />}
      {aba === "simulador" && <Simulador />}
      {aba === "historico" && <HistoricoFiscal />}
    </div>
  );
}

// ─── CFOP ──────────────────────────────────────────────────

function Cfop() {
  const [tipo, setTipo] = useState("");
  const [rows, setRows] = useState<CfopCode[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarCfop(tipo.trim() || undefined));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)} className="w-44">
            <option value="">Todos</option>
            <option value="entrada">Entrada</option>
            <option value="saida">Saída</option>
            <option value="mesma_uf">Mesma UF</option>
            <option value="outra_uf">Outra UF</option>
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Código", "Descrição", "Tipo"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={3} message="Nenhum CFOP" />
            ) : (
              rows.map((c) => (
                <tr key={c.codigo} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                  <Cell>{c.descricao}</Cell>
                  <Cell>
                    <Badge>{c.tipo}</Badge>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}

// ─── CST ───────────────────────────────────────────────────

function Cst() {
  const [tab, setTab] = useState("cst_icms");
  const [rows, setRows] = useState<CstCode[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarCst(tab));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Tabela">
          <Select value={tab} onChange={(e) => setTab(e.target.value)} className="w-44">
            <option value="cst_icms">ICMS</option>
            <option value="cst_pis">PIS</option>
            <option value="cst_cofins">COFINS</option>
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Código", "Descrição"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={2} message="Nenhum CST" />
            ) : (
              rows.map((c) => (
                <tr key={c.codigo} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                  <Cell>{c.descricao}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}

// ─── CEST ──────────────────────────────────────────────────

function Cest() {
  const [ncm, setNcm] = useState("");
  const [rows, setRows] = useState<CestItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarCest(ncm.trim() || undefined));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="NCM">
          <Input placeholder="Ex.: 8544" value={ncm} onChange={(e) => setNcm(e.target.value)} className="w-48" />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["CEST", "NCM", "Descrição", "Vigência"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={4} message="Nenhum CEST" />
            ) : (
              rows.map((c) => (
                <tr key={c.codigo} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                  <Cell className="font-mono text-xs">{c.ncm_prefix || "—"}</Cell>
                  <Cell>{c.descricao || "—"}</Cell>
                  <Cell className="text-xs">
                    {c.vigencia_inicio ? fmtDate(c.vigencia_inicio) : ""}
                    {c.vigencia_fim ? " → " + fmtDate(c.vigencia_fim) : ""}
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}

// ─── Config Fiscal ─────────────────────────────────────────

function Config() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<FiscalConfigItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [editando, setEditando] = useState<FiscalConfigItem | null>(null);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarFiscalConfig({ q: q.trim() || undefined, limit: 200 }));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const gerar = async () => {
    try {
      const r = await api.gerarFiscalConfig();
      toast(`${r.gerados} configurações geradas`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => void gerar()}>
          Gerar config padrão
        </Button>
        <Field label="Busca">
          <Input
            placeholder="Produto, SKU, NCM…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-64"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "NCM", "CFOP", "CST ICMS", "PIS", "COFINS", "ICMS%", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhuma config" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{c.produto_nome}</span>
                    {c.sku ? <div className="font-mono text-xs text-gray-400">{c.sku}</div> : null}
                  </Cell>
                  <Cell className="font-mono text-xs">{c.ncm || "—"}</Cell>
                  <Cell className="font-mono text-xs">{c.cfop ?? "—"}</Cell>
                  <Cell className="text-xs">{c.cst_icms ?? "—"}</Cell>
                  <Cell className="text-xs">{c.cst_pis ?? "—"}</Cell>
                  <Cell className="text-xs">{c.cst_cofins ?? "—"}</Cell>
                  <Cell>{c.aliquota_icms ? c.aliquota_icms + "%" : "—"}</Cell>
                  <Cell>
                    <div className="flex justify-end">
                      <Button size="sm" variant="ghost" onClick={() => setEditando(c)}>
                        Editar
                      </Button>
                    </div>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <ModalFiscal
        config={editando}
        onClose={() => setEditando(null)}
        onSaved={() => void carregar()}
      />
    </div>
  );
}

function ModalFiscal({
  config,
  onClose,
  onSaved,
}: {
  config: FiscalConfigItem | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [cests, setCests] = useState<CestItem[]>([]);
  const [csosns, setCsosns] = useState<CsosnItem[]>([]);
  const [benefs, setBenefs] = useState<BeneficioFiscalItem[]>([]);
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!config) return;
    setForm({
      ncm: config.ncm || "",
      cfop: config.cfop || "",
      origem: String(config.origem ?? 0),
      cest: config.cest || "",
      csosn: config.csosn || "",
      cst_icms: config.cst_icms || "",
      aliquota_icms: String(config.aliquota_icms || 0),
      aliquota_icms_st: String(config.aliquota_icms_st || 0),
      mva: String(config.mva || 0),
      base_reducao: String(config.base_reducao || 0),
      aliquota_interestadual: String(config.aliquota_interestadual || 0),
      aliquota_fecp: String(config.aliquota_fecp || 0),
      credito_icms: String(config.credito_icms || 0),
      beneficio_id: String(config.beneficio_id ?? ""),
      cst_pis: config.cst_pis || "",
      aliquota_pis: String(config.aliquota_pis || 0),
      cst_cofins: config.cst_cofins || "",
      aliquota_cofins: String(config.aliquota_cofins || 0),
      aliquota_ipi: String(config.aliquota_ipi || 0),
      vigencia_inicio: config.vigencia_inicio || "",
      vigencia_fim: config.vigencia_fim || "",
    });
    void Promise.all([
      api.listarCest(config.ncm || undefined),
      api.listarCsosn(),
      api.listarBeneficiosFiscais(),
    ])
      .then(([a, b, d]) => {
        setCests(a);
        setCsosns(b);
        setBenefs(d);
      })
      .catch(() => {});
  }, [config]);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const num = (k: string) => {
    const v = (form[k] || "").replace(",", ".");
    return v === "" ? undefined : parseFloat(v);
  };

  const salvar = async () => {
    if (!config) return;
    const benef = form.beneficio_id || "";
    try {
      await api.upsertFiscalConfig(config.produto_id, {
        ncm: (form.ncm || "").trim() || undefined,
        cfop: (form.cfop || "").trim() || undefined,
        origem: parseInt(form.origem || "0", 10),
        cest: form.cest || undefined,
        csosn: form.csosn || undefined,
        cst_icms: (form.cst_icms || "").trim() || undefined,
        aliquota_icms: num("aliquota_icms"),
        aliquota_icms_st: num("aliquota_icms_st"),
        mva: num("mva"),
        base_reducao: num("base_reducao"),
        aliquota_interestadual: num("aliquota_interestadual"),
        aliquota_fecp: num("aliquota_fecp"),
        credito_icms: num("credito_icms"),
        beneficio_id: benef ? parseInt(benef, 10) : null,
        cst_pis: (form.cst_pis || "").trim() || undefined,
        aliquota_pis: num("aliquota_pis"),
        cst_cofins: (form.cst_cofins || "").trim() || undefined,
        aliquota_cofins: num("aliquota_cofins"),
        aliquota_ipi: num("aliquota_ipi"),
        vigencia_inicio: form.vigencia_inicio || null,
        vigencia_fim: form.vigencia_fim || null,
      });
      toast("Config salva", "success");
      onClose();
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={config !== null}
      onClose={onClose}
      title={`Config Fiscal — ${config?.produto_nome ?? ""}`}
      wide
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
        <Field label="NCM">
          <Input maxLength={8} value={form.ncm || ""} onChange={(e) => set("ncm", e.target.value)} />
        </Field>
        <Field label="CFOP">
          <Input maxLength={4} value={form.cfop || ""} onChange={(e) => set("cfop", e.target.value)} />
        </Field>
        <Field label="Origem">
          <Select value={form.origem || "0"} onChange={(e) => set("origem", e.target.value)}>
            {ORIGENS.map((t, i) => (
              <option key={i} value={i}>
                {i} · {t}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="CEST">
          <Select value={form.cest || ""} onChange={(e) => set("cest", e.target.value)}>
            <option value="">—</option>
            {cests.map((x) => (
              <option key={x.codigo} value={x.codigo}>
                {`${x.codigo} · ${x.descricao || ""}`.trim()}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="CSOSN (Simples)">
          <Select value={form.csosn || ""} onChange={(e) => set("csosn", e.target.value)}>
            <option value="">—</option>
            {csosns.map((x) => (
              <option key={x.codigo} value={x.codigo}>
                {`${x.codigo} · ${x.descricao}`}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Benefício fiscal">
          <Select value={form.beneficio_id || ""} onChange={(e) => set("beneficio_id", e.target.value)}>
            <option value="">Nenhum</option>
            {benefs.map((x) => (
              <option key={x.id} value={x.id}>
                {x.descricao}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="CST ICMS">
          <Input maxLength={2} value={form.cst_icms || ""} onChange={(e) => set("cst_icms", e.target.value)} />
        </Field>
        <Field label="Alíq. ICMS %">
          <Input type="number" step="0.01" value={form.aliquota_icms || ""} onChange={(e) => set("aliquota_icms", e.target.value)} />
        </Field>
        <Field label="Alíq. ICMS-ST %">
          <Input type="number" step="0.01" value={form.aliquota_icms_st || ""} onChange={(e) => set("aliquota_icms_st", e.target.value)} />
        </Field>
        <Field label="MVA %">
          <Input type="number" step="0.01" value={form.mva || ""} onChange={(e) => set("mva", e.target.value)} />
        </Field>
        <Field label="Redução base %">
          <Input type="number" step="0.01" value={form.base_reducao || ""} onChange={(e) => set("base_reducao", e.target.value)} />
        </Field>
        <Field label="Alíq. Interestadual %">
          <Input type="number" step="0.01" value={form.aliquota_interestadual || ""} onChange={(e) => set("aliquota_interestadual", e.target.value)} />
        </Field>
        <Field label="FECP %">
          <Input type="number" step="0.01" value={form.aliquota_fecp || ""} onChange={(e) => set("aliquota_fecp", e.target.value)} />
        </Field>
        <Field label="Crédito ICMS %">
          <Input type="number" step="0.01" value={form.credito_icms || ""} onChange={(e) => set("credito_icms", e.target.value)} />
        </Field>
        <Field label="CST PIS">
          <Input maxLength={2} value={form.cst_pis || ""} onChange={(e) => set("cst_pis", e.target.value)} />
        </Field>
        <Field label="Alíq. PIS %">
          <Input type="number" step="0.01" value={form.aliquota_pis || ""} onChange={(e) => set("aliquota_pis", e.target.value)} />
        </Field>
        <Field label="CST COFINS">
          <Input maxLength={2} value={form.cst_cofins || ""} onChange={(e) => set("cst_cofins", e.target.value)} />
        </Field>
        <Field label="Alíq. COFINS %">
          <Input type="number" step="0.01" value={form.aliquota_cofins || ""} onChange={(e) => set("aliquota_cofins", e.target.value)} />
        </Field>
        <Field label="Alíq. IPI %">
          <Input type="number" step="0.01" value={form.aliquota_ipi || ""} onChange={(e) => set("aliquota_ipi", e.target.value)} />
        </Field>
        <Field label="Vigência início">
          <Input type="date" value={form.vigencia_inicio || ""} onChange={(e) => set("vigencia_inicio", e.target.value)} />
        </Field>
        <Field label="Vigência fim">
          <Input type="date" value={form.vigencia_fim || ""} onChange={(e) => set("vigencia_fim", e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

// ─── Emitente ──────────────────────────────────────────────

function EmitenteTab() {
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    void api
      .getEmitente()
      .then((e) => {
        const r = e as unknown as Record<string, unknown>;
        const s = (v: unknown, fb = "") => (v == null ? fb : String(v));
        setForm({
          razao_social: s(r.razao_social),
          cnpj: s(r.cnpj),
          ie: s(r.ie),
          regime_tributario: s(r.regime_tributario, "simples_nacional"),
          crt: s(r.crt, "1"),
          token_focus: s(r.token_focus),
          aliquota_icms: s(r.aliquota_icms, "18"),
          aliquota_ibs: s(r.aliquota_ibs, "0"),
          aliquota_cbs: s(r.aliquota_cbs, "0"),
          ibs_vigencia_inicio: s(r.ibs_vigencia_inicio),
          ibs_vigencia_fim: s(r.ibs_vigencia_fim),
          cbs_vigencia_inicio: s(r.cbs_vigencia_inicio),
          cbs_vigencia_fim: s(r.cbs_vigencia_fim),
        });
      })
      .catch(() => {});
  }, []);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const salvar = async () => {
    try {
      await api.upsertEmitente({
        razao_social: (form.razao_social || "").trim(),
        cnpj: (form.cnpj || "").trim(),
        ie: (form.ie || "").trim(),
        regime_tributario: form.regime_tributario || "simples_nacional",
        crt: parseInt(form.crt || "1", 10) || 1,
        token_focus: (form.token_focus || "").trim(),
        aliquota_icms: parseFloat(form.aliquota_icms || "0"),
        aliquota_ibs: parseFloat(form.aliquota_ibs || "0"),
        aliquota_cbs: parseFloat(form.aliquota_cbs || "0"),
        ibs_vigencia_inicio: form.ibs_vigencia_inicio || null,
        ibs_vigencia_fim: form.ibs_vigencia_fim || null,
        cbs_vigencia_inicio: form.cbs_vigencia_inicio || null,
        cbs_vigencia_fim: form.cbs_vigencia_fim || null,
      });
      toast("Emitente salvo", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <Field label="Razão Social">
        <Input value={form.razao_social || ""} onChange={(e) => set("razao_social", e.target.value)} />
      </Field>
      <Field label="CNPJ">
        <Input value={form.cnpj || ""} onChange={(e) => set("cnpj", e.target.value)} />
      </Field>
      <Field label="IE">
        <Input value={form.ie || ""} onChange={(e) => set("ie", e.target.value)} />
      </Field>
      <Field label="Regime Tributário">
        <Select value={form.regime_tributario || "simples_nacional"} onChange={(e) => set("regime_tributario", e.target.value)}>
          <option value="simples_nacional">Simples Nacional</option>
          <option value="lucro_presumido">Lucro Presumido</option>
          <option value="lucro_real">Lucro Real</option>
        </Select>
      </Field>
      <Field label="CRT">
        <Select value={form.crt || "1"} onChange={(e) => set("crt", e.target.value)}>
          <option value="1">1 — Simples Nacional</option>
          <option value="2">2 — Simples (excesso de sublimite)</option>
          <option value="3">3 — Regime Normal</option>
        </Select>
      </Field>
      <Field label="Token Focus NFe">
        <Input type="password" value={form.token_focus || ""} onChange={(e) => set("token_focus", e.target.value)} />
      </Field>
      <Field label="Alíq. ICMS %">
        <Input type="number" step="0.01" value={form.aliquota_icms || ""} onChange={(e) => set("aliquota_icms", e.target.value)} />
      </Field>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Alíq. IBS % (transição — validar)">
          <Input type="number" step="0.01" value={form.aliquota_ibs || ""} onChange={(e) => set("aliquota_ibs", e.target.value)} />
        </Field>
        <Field label="Alíq. CBS % (transição — validar)">
          <Input type="number" step="0.01" value={form.aliquota_cbs || ""} onChange={(e) => set("aliquota_cbs", e.target.value)} />
        </Field>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Vigência IBS início">
          <Input type="date" value={form.ibs_vigencia_inicio || ""} onChange={(e) => set("ibs_vigencia_inicio", e.target.value)} />
        </Field>
        <Field label="Vigência IBS fim">
          <Input type="date" value={form.ibs_vigencia_fim || ""} onChange={(e) => set("ibs_vigencia_fim", e.target.value)} />
        </Field>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Vigência CBS início">
          <Input type="date" value={form.cbs_vigencia_inicio || ""} onChange={(e) => set("cbs_vigencia_inicio", e.target.value)} />
        </Field>
        <Field label="Vigência CBS fim">
          <Input type="date" value={form.cbs_vigencia_fim || ""} onChange={(e) => set("cbs_vigencia_fim", e.target.value)} />
        </Field>
      </div>
      <Button variant="primary" onClick={() => void salvar()}>
        Salvar emitente
      </Button>
    </div>
  );
}

// ─── NF-e ──────────────────────────────────────────────────

function Nfe() {
  const [sub, setSub] = useState<"saida" | "entrada">("saida");
  const [saida, setSaida] = useState<NfeSaida[]>([]);
  const [entrada, setEntrada] = useState<NfeEntrada[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    setCarregando(true);
    if (sub === "saida") {
      void api
        .listarNfeSaida()
        .then(setSaida)
        .catch(() => setSaida([]))
        .finally(() => setCarregando(false));
    } else {
      void api
        .listarNfeEntrada()
        .then(setEntrada)
        .catch(() => setEntrada([]))
        .finally(() => setCarregando(false));
    }
  }, [sub]);

  return (
    <div>
      <div className="mb-5 flex flex-wrap gap-2 border-b border-gray-200">
        {(["saida", "entrada"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setSub(s)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              sub === s ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {s === "saida" ? "Saída" : "Entrada"}
          </button>
        ))}
      </div>

      {carregando ? (
        <Loading />
      ) : sub === "saida" ? (
        saida.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
            Nenhuma NF-e de saída
          </div>
        ) : (
          <Table>
            <THead cols={["Nº", "Cliente", "Valor", "Status", "Data"]} />
            <TBody>
              {saida.map((n) => (
                <tr key={n.id} className="hover:bg-gray-50">
                  <Cell className="font-mono">{n.numero}</Cell>
                  <Cell>{n.cliente_nome}</Cell>
                  <Cell>{fmtMoney(n.valor)}</Cell>
                  <Cell>
                    <Badge tone={n.status === "autorizada" ? "green" : "gray"}>{n.status}</Badge>
                  </Cell>
                  <Cell className="text-xs">{fmtDate(n.criado_em)}</Cell>
                </tr>
              ))}
            </TBody>
          </Table>
        )
      ) : entrada.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhuma NF-e de entrada
        </div>
      ) : (
        <Table>
          <THead cols={["Chave", "Fornecedor", "Valor", "Emissão"]} />
          <TBody>
            {entrada.map((n) => (
              <tr key={n.id} className="hover:bg-gray-50">
                <Cell className="font-mono text-xs">{n.chave}</Cell>
                <Cell>{n.fornecedor_nome}</Cell>
                <Cell>{fmtMoney(n.valor)}</Cell>
                <Cell className="text-xs">{fmtDate(n.data_emissao)}</Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}

// ─── IBPT ──────────────────────────────────────────────────

function Ibpt() {
  const [ncm, setNcm] = useState("");
  const [rows, setRows] = useState<IbptItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarIbpt({ ncm: ncm.trim() || undefined, limit: 50 }));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="NCM">
          <Input
            placeholder="Buscar NCM…"
            value={ncm}
            onChange={(e) => setNcm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-48"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["NCM", "Federal%", "Estadual%", "Municipal%"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={4} message="Nenhum" />
            ) : (
              rows.map((i) => (
                <tr key={i.id} className="hover:bg-gray-50">
                  <Cell className="font-mono">{i.ncm}</Cell>
                  <Cell>{i.aliquota_federal}%</Cell>
                  <Cell>{i.aliquota_estadual}%</Cell>
                  <Cell>{i.aliquota_municipal}%</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}

// ─── Histórico (auditoria) ─────────────────────────────────

function HistoricoFiscal() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<HistoricoFiscalItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setRows(await api.listarHistoricoFiscal({ q: q.trim() || undefined }));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Busca">
          <Input
            placeholder="Produto, SKU, NCM…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-64"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Produto", "Tipo", "NCM", "CEST", "CSOSN", "ICMS%", "ST%", "MVA%", "Por"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={10} message="Nenhum registro" />
            ) : (
              rows.map((h) => (
                <tr key={h.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDateTime(h.criado_em)}</Cell>
                  <Cell>
                    <span className="font-medium">{h.produto_nome}</span>
                    {h.sku ? <div className="font-mono text-xs text-gray-400">{h.sku}</div> : null}
                  </Cell>
                  <Cell>
                    <Badge tone={h.tipo === "criado" ? "gray" : "green"}>{h.tipo}</Badge>
                  </Cell>
                  <Cell className="font-mono text-xs">{h.ncm || "—"}</Cell>
                  <Cell className="font-mono text-xs">{h.cest || "—"}</Cell>
                  <Cell className="text-xs">{h.csosn || "—"}</Cell>
                  <Cell>{h.aliquota_icms ? h.aliquota_icms + "%" : "—"}</Cell>
                  <Cell>{h.aliquota_icms_st ? h.aliquota_icms_st + "%" : "—"}</Cell>
                  <Cell>{h.mva ? h.mva + "%" : "—"}</Cell>
                  <Cell>{h.usuario_nome ?? "—"}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}

// ─── Simulador fiscal ──────────────────────────────────────

function Simulador() {
  const [busca, setBusca] = useState("");
  const [cliBusca, setCliBusca] = useState("");
  const [uf, setUf] = useState("");
  const [tipoCliente, setTipoCliente] = useState("");
  const [contribuinte, setContribuinte] = useState("");
  const [modelo, setModelo] = useState("");
  const [operacao, setOperacao] = useState("venda");
  const [data, setData] = useState(new Date().toISOString().slice(0, 10));
  const [qtd, setQtd] = useState("1");
  const [valor, setValor] = useState("100");
  const [desconto, setDesconto] = useState("0");

  const [sugProd, setSugProd] = useState<ProdutoResumo[]>([]);
  const [sugCli, setSugCli] = useState<Cliente[]>([]);
  const [selecionada, setSelecionada] = useState<ProdutoResumo | null>(null);
  const [clienteId, setClienteId] = useState<number | null>(null);
  const [clienteNome, setClienteNome] = useState<string | null>(null);
  const [resultado, setResultado] = useState<FiscalResultado | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const timerP = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const timerC = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    clearTimeout(timerP.current);
    if (!busca.trim()) {
      setSugProd([]);
      return;
    }
    timerP.current = setTimeout(() => {
      void api
        .listarProdutos({ q: busca.trim(), limit: 8, agrupado: 0 })
        .then((res) => setSugProd(res.items.filter((i): i is ProdutoResumo => "price" in i)))
        .catch(() => setSugProd([]));
    }, 200);
    return () => clearTimeout(timerP.current);
  }, [busca]);

  useEffect(() => {
    clearTimeout(timerC.current);
    if (!cliBusca.trim()) {
      setSugCli([]);
      return;
    }
    timerC.current = setTimeout(() => {
      void api
        .buscarClientes(cliBusca.trim())
        .then(setSugCli)
        .catch(() => setSugCli([]));
    }, 200);
    return () => clearTimeout(timerC.current);
  }, [cliBusca]);

  const simular = async () => {
    if (!selecionada) {
      toast("Selecione um produto", "error");
      return;
    }
    const payload: Record<string, unknown> = {
      variante_id: selecionada.id,
      operacao,
      data: data || undefined,
      quantidade: parseFloat(qtd || "1"),
      valor_unitario: parseFloat(valor || "0"),
      desconto: parseFloat(desconto || "0"),
      uf_destino: uf.trim().toUpperCase() || undefined,
      tipo_cliente: tipoCliente || undefined,
      contribuinte: contribuinte || undefined,
      modelo_documento: modelo || undefined,
    };
    if (clienteId) payload.cliente_id = clienteId;
    setCarregando(true);
    setErro("");
    setResultado(null);
    try {
      const sim = await api.simularFiscal(payload);
      setResultado(sim.resultado);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Produto" className="min-w-[260px]">
          <Input placeholder="Nome, SKU…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </Field>
        <Field label="Cliente (opcional)" className="min-w-[200px]">
          <Input placeholder="Nome, CPF…" value={cliBusca} onChange={(e) => setCliBusca(e.target.value)} />
        </Field>
        <Field label="UF destino">
          <Input maxLength={2} value={uf} onChange={(e) => setUf(e.target.value)} className="w-20" />
        </Field>
        <Field label="Tipo cliente">
          <Select value={tipoCliente} onChange={(e) => setTipoCliente(e.target.value)} className="w-32">
            <option value="">—</option>
            <option value="PF">PF</option>
            <option value="PJ">PJ</option>
          </Select>
        </Field>
        <Field label="Contribuinte">
          <Select value={contribuinte} onChange={(e) => setContribuinte(e.target.value)} className="w-44">
            <option value="">—</option>
            <option value="contribuinte">Contribuinte</option>
            <option value="nao_contribuinte">Não contribuinte</option>
          </Select>
        </Field>
        <Field label="Modelo">
          <Select value={modelo} onChange={(e) => setModelo(e.target.value)} className="w-32">
            <option value="">—</option>
            <option value="55">NF-e 55</option>
            <option value="65">NFC-e 65</option>
          </Select>
        </Field>
        <Field label="Operação">
          <Select value={operacao} onChange={(e) => setOperacao(e.target.value)} className="w-32">
            <option value="venda">Venda</option>
            <option value="compra">Compra</option>
          </Select>
        </Field>
        <Field label="Data">
          <Input type="date" value={data} onChange={(e) => setData(e.target.value)} className="w-40" />
        </Field>
        <Field label="Qtd">
          <Input type="number" min={0} step="any" value={qtd} onChange={(e) => setQtd(e.target.value)} className="w-20" />
        </Field>
        <Field label="Valor unit.">
          <Input type="number" min={0} step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} className="w-24" />
        </Field>
        <Field label="Desconto">
          <Input type="number" min={0} step="0.01" value={desconto} onChange={(e) => setDesconto(e.target.value)} className="w-20" />
        </Field>
        <Button variant="primary" onClick={() => void simular()}>
          Simular
        </Button>
      </div>

      {sugProd.length > 0 ? (
        <div className="mb-3 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {sugProd.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setSelecionada(p);
                setSugProd([]);
                setResultado(null);
              }}
              className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-gray-50"
            >
              <span className="font-medium">
                {p.name}
                {p.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{p.sku}</span> : null}
              </span>
            </button>
          ))}
        </div>
      ) : null}

      {sugCli.length > 0 ? (
        <div className="mb-3 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {sugCli.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => {
                setClienteId(c.id);
                setClienteNome(c.nome);
                setSugCli([]);
              }}
              className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-gray-50"
            >
              <span className="font-medium">
                {c.nome}
                {c.doc ? <span className="ml-2 font-mono text-xs text-gray-400">{c.doc}</span> : null}
              </span>
            </button>
          ))}
        </div>
      ) : null}

      {selecionada ? (
        <p className="mb-2 text-sm text-gray-600">
          Produto: <span className="font-medium">{selecionada.name}</span>
          {selecionada.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{selecionada.sku}</span> : null}
        </p>
      ) : null}
      {clienteNome ? <p className="mb-2 text-sm text-gray-600">Cliente: <span className="font-medium">{clienteNome}</span></p> : null}

      {carregando ? <Loading message="Calculando…" /> : null}
      {erro ? <div className="py-4 text-center text-sm text-gray-400">Erro: {erro}</div> : null}

      {resultado ? <ResultadoFiscal r={resultado} /> : null}
    </div>
  );
}

function ResultadoFiscal({ r }: { r: FiscalResultado }) {
  const linha = (rot: string, val: string) => (
    <tr>
      <td className="px-4 py-2 text-xs text-gray-500">{rot}</td>
      <td className="px-4 py-2 text-right font-medium">{val}</td>
    </tr>
  );
  const memoria = r.memoria as Record<string, unknown>;
  const memoriaProduto = r.memoria_produto as Record<string, unknown> | null;

  return (
    <div className="max-w-2xl rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 font-semibold text-gray-900">
        Simulação — {r.cfop || "—"}{" "}
        <Badge tone={r.status_validacao === "erro" ? "red" : "green"}>
          {r.status_validacao === "erro" ? "ERROR (bloqueado)" : "ok"}
        </Badge>
      </h3>
      <Table>
        <TBody>
          {linha("NCM / CEST", `${r.ncm || "—"}${r.cest ? " · " + r.cest : ""}`)}
          {linha("CFOP", r.cfop || "—")}
          {linha(
            "CST / CSOSN",
            `${r.cst_icms || r.csosn || "—"}${r.cst_ibs || r.cst_cbs ? ` · IBS ${r.cst_ibs || "—"} / CBS ${r.cst_cbs || "—"}` : ""}`
          )}
          {linha("ICMS", `base ${fmtMoney(r.base_icms)} · ${r.aliquota_icms}% · ${fmtMoney(r.valor_icms)}`)}
          {linha("ICMS-ST", r.valor_icms_st ? `base ${fmtMoney(r.base_icms_st)} · ${r.aliquota_icms_st}% · ${fmtMoney(r.valor_icms_st)}` : "—")}
          {linha("PIS / COFINS", `${fmtMoney(r.valor_pis)} / ${fmtMoney(r.valor_cofins)}`)}
          {linha("IBS / CBS", `${fmtMoney(r.valor_ibs)} / ${fmtMoney(r.valor_cbs)}`)}
        </TBody>
      </Table>
      <p className="mt-2 text-xs text-gray-500">
        Regra: <span className="font-medium">{String(memoria.regra_nome || "configuração do produto")}</span>
        {memoria.versao ? ` · versão ${String(memoria.versao)}` : ""}
        {memoriaProduto ? ` · Produto: ${String(memoriaProduto.regra_nome || "")}` : ""}
      </p>
      {(r.problemas || []).length > 0 ? (
        <div className="mt-3">
          <h4 className="text-sm font-medium text-gray-700">Validação</h4>
          <ul className="mt-1 space-y-1">
            {(r.problemas || []).map((p, i) => (
              <li
                key={i}
                className={`text-xs ${
                  p.tipo === "ERROR" ? "text-red-600" : p.tipo === "WARNING" ? "text-amber-600" : "text-gray-500"
                }`}
              >
                <span className="font-semibold">{p.tipo}</span> · {p.campo} — {p.mensagem}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-medium text-gray-600">Árvore de decisão (por que essa regra?)</summary>
        <ul className="mt-2 space-y-1 text-xs text-gray-600">
          {(r.decisao || []).length === 0 ? (
            <li>—</li>
          ) : (
            (r.decisao || []).map((d, i) => (
              <li key={i}>
                <span className="font-semibold">{d.passo}</span>: {d.detalhe}
              </li>
            ))
          )}
        </ul>
      </details>
    </div>
  );
}

// ─── Sugestões de NCM (IBPT) ──────────────────────────────

function Sugestoes() {
  const [status, setStatus] = useState("pendente");
  const [conf, setConf] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<SugestaoIbpt[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      const confianca_min = parseFloat(conf) || undefined;
      setRows(await api.listarSugestoesIbpt({ status, confianca_min, q: q.trim() || undefined, limit: 200 }));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const revisar = async (id: number, s: "aplicada" | "rejeitada", msg: string) => {
    try {
      await api.revisarSugestaoIbpt(id, s);
      toast(msg, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const gerar = async () => {
    const confianca_min = parseFloat(conf || "40") || 40;
    try {
      const r = await api.gerarSugestoesIbpt({ confianca_min });
      toast(`${r.sugestoes} sugestões geradas`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const aplicarTodas = async () => {
    const confianca_min = parseFloat(conf || "0") || 0;
    if (!window.confirm(`Aplicar TODAS as sugestões pendentes com confiança ≥ ${confianca_min}%?`)) return;
    try {
      const r = await api.aplicarSugestoesIbpt({ confianca_min });
      toast(`${r.aplicadas} NCMs aplicadas`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Status">
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-36">
            <option value="pendente">Pendentes</option>
            <option value="aplicada">Aplicadas</option>
            <option value="rejeitada">Rejeitadas</option>
            <option value="">Todas</option>
          </Select>
        </Field>
        <Field label="Confiança mín. %">
          <Input type="number" min={0} max={100} step={1} placeholder="ex.: 50" value={conf} onChange={(e) => setConf(e.target.value)} className="w-28" />
        </Field>
        <Field label="Busca">
          <Input
            placeholder="Produto, SKU, NCM…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-56"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
        <Button variant="primary" onClick={() => void gerar()}>
          Gerar sugestões
        </Button>
        <Button onClick={() => void aplicarTodas()}>Aplicar pendentes ≥ X%</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "NCM sugerido", "Descrição IBPT", "Confiança", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhuma sugestão" />
            ) : (
              rows.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{s.produto_nome}</span>
                    {s.sku ? <div className="font-mono text-xs text-gray-400">{s.sku}</div> : null}
                  </Cell>
                  <Cell className="font-mono font-semibold">{s.ncm}</Cell>
                  <Cell className="text-xs text-gray-500">{s.descricao || "—"}</Cell>
                  <Cell>
                    <Badge tone={s.confianca >= 70 ? "green" : s.confianca >= 40 ? "gray" : "red"}>{s.confianca.toFixed(0)}%</Badge>
                  </Cell>
                  <Cell>
                    <Badge tone={s.status === "aplicada" ? "green" : s.status === "rejeitada" ? "red" : "gray"}>{s.status}</Badge>
                  </Cell>
                  <Cell>
                    {s.status === "pendente" ? (
                      <div className="flex justify-end gap-2">
                        <Button size="sm" onClick={() => void revisar(s.id, "aplicada", "NCM aplicada")}>
                          Aplicar
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => void revisar(s.id, "rejeitada", "Sugestão rejeitada")}>
                          Rejeitar
                        </Button>
                      </div>
                    ) : null}
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}
