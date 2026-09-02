import { useEffect, useMemo, useState } from "react";
import { BookOpen, ChevronRight, CircleHelp, Keyboard, Search } from "lucide-react";
import { Badge, Button, Card } from "../ui/ui";
import { buscarManual, type ManualQuickEntry } from "../manual-content";

function EntryDetail({ entry }: { entry: ManualQuickEntry }) {
  return (
    <div id={entry.id}>
      <Card className="overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50/80 px-4 py-4 sm:px-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="blue">{entry.group}</Badge>
          <span className="font-mono text-xs text-slate-500">{entry.route}</span>
        </div>
        <h2 className="mt-2 text-xl font-bold tracking-tight text-slate-900">{entry.title}</h2>
      </div>
      <div className="grid gap-5 px-4 py-5 sm:px-5 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-4 text-sm leading-6 text-slate-700">
          <section><h3 className="font-semibold text-slate-900">O que é?</h3><p>{entry.what}</p></section>
          <section><h3 className="font-semibold text-slate-900">Para que serve?</h3><p>{entry.purpose}</p></section>
          <section><h3 className="font-semibold text-slate-900">Qual é o papel no sistema?</h3><p>{entry.role}</p></section>
          <section><h3 className="font-semibold text-slate-900">Quem pode usar?</h3><p>{entry.access}</p></section>
          <section><h3 className="font-semibold text-slate-900">Pré-requisitos</h3><p>{entry.prerequisites}</p></section>
        </div>
        <div className="space-y-4 text-sm leading-6 text-slate-700">
          <section>
            <h3 className="font-semibold text-slate-900">Passo a passo</h3>
            <ol className="mt-1 list-decimal space-y-1 pl-5">{entry.steps.map((step) => <li key={step}>{step}</li>)}</ol>
          </section>
          {entry.shortcuts ? <section><h3 className="flex items-center gap-1.5 font-semibold text-slate-900"><Keyboard size={15} /> Atalhos</h3><p>{entry.shortcuts}</p></section> : null}
          <section className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2"><h3 className="font-semibold text-amber-900">Atenção</h3><p className="text-amber-900/90">{entry.cautions}</p></section>
          <section><h3 className="font-semibold text-slate-900">Auditoria</h3><p>{entry.audit}</p></section>
          <a className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline" href={entry.route}>Abrir tela <ChevronRight size={15} /></a>
        </div>
      </div>
      </Card>
    </div>
  );
}

export default function Manual() {
  const [term, setTerm] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const entries = useMemo(() => buscarManual(term), [term]);
  const selected = selectedId ? entries.find((entry) => entry.id === selectedId) : undefined;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "/") {
        event.preventDefault();
        document.getElementById("manual-search")?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-brand-900 px-5 py-6 text-white shadow-lg sm:px-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-brand-200"><BookOpen size={18} /><span className="text-xs font-bold uppercase tracking-[0.16em]">Central de ajuda</span></div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">Manual do ERP</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">Consulte rapidamente o que cada tela faz, quem pode utilizá-la e quais efeitos ela produz no negócio.</p>
          </div>
          <CircleHelp className="text-brand-300" size={40} strokeWidth={1.4} aria-hidden="true" />
        </div>
        <div className="relative mt-5 max-w-2xl">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={17} aria-hidden="true" />
          <label className="sr-only" htmlFor="manual-search">Pesquisar no manual</label>
          <input id="manual-search" value={term} onChange={(event) => setTerm(event.target.value)} placeholder="Pesquisar módulo, tarefa ou palavra-chave (Ctrl+/)" className="w-full rounded-lg border border-white/20 bg-white px-10 py-3 text-sm text-slate-900 shadow-sm outline-none focus:ring-2 focus:ring-brand-300" />
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600">
        <span>{entries.length} módulo(s) encontrado(s)</span>
        {term ? <Button size="sm" variant="ghost" onClick={() => { setTerm(""); setSelectedId(null); }}>Limpar pesquisa</Button> : <span>Atualizado para a versão em desenvolvimento</span>}
      </div>

      {selected ? <EntryDetail entry={selected} /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {entries.map((entry) => (
            <button key={entry.id} type="button" onClick={() => setSelectedId(entry.id)} className="rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-brand-500/40">
              <div className="flex items-center justify-between gap-3"><Badge tone="blue">{entry.group}</Badge><ChevronRight size={17} className="text-slate-400" /></div>
              <h2 className="mt-3 font-semibold text-slate-900">{entry.title}</h2>
              <p className="mt-1 text-sm leading-5 text-slate-600">{entry.what}</p>
              <span className="mt-3 block font-mono text-[11px] text-slate-400">{entry.route}</span>
            </button>
          ))}
        </div>
      )}

      {entries.length === 0 ? <Card className="py-12 text-center"><p className="font-medium text-slate-800">Nenhum módulo encontrado</p><p className="mt-1 text-sm text-slate-500">Tente buscar por venda, estoque, crédito, compra ou relatório.</p></Card> : null}
      <p className="text-xs leading-5 text-slate-500">A documentação operacional completa, com screenshots anonimizados, fica em <code>docs/wiki/</code>. Se uma regra desta página divergir da API, o backend é a autoridade.</p>
    </div>
  );
}
