// pages/fiscal/modal-fiscal.tsx - módulo Fiscal (ModalFiscal).

import { useEffect, useState } from "react";
import { api, type BeneficioFiscalItem, type CestItem, type CsosnItem, type FiscalConfigItem } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select } from "../../ui/ui";

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

export function ModalFiscal({
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


