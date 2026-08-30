// pages/fiscal/emitente-tab.tsx - módulo Fiscal (EmitenteTab).

import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Select } from "../../ui/ui";

export function EmitenteTab() {
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


