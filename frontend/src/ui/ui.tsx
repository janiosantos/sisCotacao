// ui/ui.tsx — componentes React + Tailwind reutilizáveis do ERP.

import {
  Children,
  cloneElement,
  forwardRef,
  isValidElement,
  useEffect,
  useId,
  useRef,
  type ReactElement,
  type ReactNode,
} from "react";
import { X } from "lucide-react";
import { temPermissao } from "../perm";

// ------------------------------------------------------------------
// Botão
// ------------------------------------------------------------------

type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";

const BTN_VARIANTS: Record<BtnVariant, string> = {
  primary: "bg-brand-600 text-white shadow-sm hover:bg-brand-700 hover:shadow focus-visible:ring-2 focus-visible:ring-brand-500/40",
  secondary: "border border-slate-300 bg-white text-slate-700 shadow-sm hover:border-slate-400 hover:bg-slate-50",
  ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  danger: "bg-red-600 text-white shadow-sm hover:bg-red-700",
  outline: "border border-brand-600 text-brand-700 hover:bg-brand-50",
};

export const Button = forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: BtnVariant;
    size?: "sm" | "md";
    permission?: { recurso: string; acao: string };
  }
>(function Button({ children, variant = "secondary", size = "md", className = "", permission, disabled, ...props }, ref) {
  const sizeCls = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm";
  const permitido = !permission || temPermissao(permission.recurso, permission.acao);
  return (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md font-semibold tracking-[-0.01em] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 ${BTN_VARIANTS[variant]} ${sizeCls} ${className}`}
      {...props}
      disabled={disabled || !permitido}
      aria-disabled={!permitido || undefined}
      title={!permitido ? "Seu perfil não possui esta permissão" : props.title}
    >
      {children}
    </button>
  );
});

// ------------------------------------------------------------------
// Card / StatCard
// ------------------------------------------------------------------

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200/90 bg-white shadow-[0_1px_2px_rgb(16_24_40/4%)] ${className}`}>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "highlight" | "danger" | "success";
}) {
  const toneCls =
    tone === "highlight"
      ? "border-brand-600"
      : tone === "danger"
        ? "border-red-400"
        : tone === "success"
          ? "border-emerald-400"
          : "border-gray-200";
  const valueCls =
    tone === "danger" ? "text-red-600" : tone === "success" ? "text-emerald-600" : "text-gray-900";
  return (
    <Card className={`border-l-4 p-4 ${toneCls}`}>
      <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-slate-500">{label}</div>
      <div className={`mt-1.5 text-[1.65rem] font-semibold leading-none tracking-[-0.03em] ${valueCls}`}>{value}</div>
      {sub ? <div className="mt-2 text-xs text-slate-500">{sub}</div> : null}
    </Card>
  );
}

// ------------------------------------------------------------------
// Badge
// ------------------------------------------------------------------

export function Badge({
  children,
  tone = "gray",
}: {
  children: ReactNode;
  tone?: "gray" | "green" | "red" | "amber" | "blue";
}) {
  const tones: Record<string, string> = {
    gray: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-700",
    red: "bg-red-100 text-red-700",
    amber: "bg-amber-100 text-amber-700",
    blue: "bg-brand-100 text-brand-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

// ------------------------------------------------------------------
// Tabela — desktop: colunas; mobile (< lg): cada linha vira um card
// com rótulos (labels do cabeçalho) para leitura sem rolagem horizontal.
// ------------------------------------------------------------------

function toText(n: ReactNode): string {
  if (n == null) return "";
  if (typeof n === "string" || typeof n === "number") return String(n);
  if (Array.isArray(n)) return n.map(toText).join(" ");
  return "";
}

export function Table({ children }: { children: ReactNode }) {
  // Extrai os labels do THead para alimentar os cards no mobile.
  const labels: ReactNode[] = [];
  Children.forEach(children, (child) => {
    if (isValidElement(child) && (child.type as { name?: string } | null)?.name === "THead") {
      const cols = (child.props as { cols?: ReactNode[] }).cols;
      if (Array.isArray(cols)) labels.push(...cols);
    }
  });
  const rows = Children.map(children, (child) => {
    if (isValidElement(child) && (child.type as { name?: string } | null)?.name === "TBody") {
      return cloneElement(child as ReactElement<{ labels?: ReactNode[] }>, { labels });
    }
    return child;
  });
  return (
    <div className="erp-scrollbar overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-[0_1px_2px_rgb(16_24_40/4%)]">
      <table className="mob-card w-full text-[13px] lg:min-w-full lg:table-fixed lg:divide-y lg:divide-slate-200">
        {rows}
      </table>
    </div>
  );
}

export function THead({
  cols,
  onSort,
  sortState,
}: {
  cols: ReactNode[];
  onSort?: (i: number) => void;
  sortState?: { index: number; dir: "asc" | "desc" };
}) {
  return (
    <thead className="hidden bg-slate-50/90 lg:table-header-group">
      <tr>
        {cols.map((c, i) => {
          const ordenavel = onSort !== undefined;
          const active = sortState?.index === i;
          const ariaSort = active ? (sortState!.dir === "asc" ? "ascending" : "descending") : ordenavel ? "none" : undefined;
          return (
            <th
              key={i}
              scope="col"
              aria-sort={ariaSort}
              className="sticky top-0 z-10 border-b border-slate-200 px-4 py-3 text-left text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500"
            >
              {ordenavel ? (
                <button
                  type="button"
                  className="flex items-center gap-1 rounded hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 focus-visible:ring-offset-1"
                  onClick={() => onSort(i)}
                  aria-label={`ordenar por ${typeof c === "string" ? c : `coluna ${i + 1}`}`}
                >
                  {c}
                  <span aria-hidden="true" className="text-[9px]">{active ? (sortState!.dir === "asc" ? "▲" : "▼") : "⇅"}</span>
                </button>
              ) : (
                c
              )}
            </th>
          );
        })}
      </tr>
    </thead>
  );
}

export function TBody({
  children,
  labels = [],
}: {
  children: ReactNode;
  labels?: ReactNode[];
}) {
  // Injeta o rótulo do cabeçalho em cada célula (usado no card do mobile).
  // Células com `data-label` explícito (ex.: EmptyRow) são preservadas.
  const rows = Children.map(children, (tr) => {
    if (!isValidElement(tr)) return tr;
    const trEl = tr as ReactElement<{ children?: ReactNode }>;
    return cloneElement(trEl, {
      children: Children.map(trEl.props.children, (cell, i) => {
        if (!isValidElement(cell)) return cell;
        const cellEl = cell as ReactElement<Record<string, unknown>>;
        const props = cellEl.props as Record<string, unknown>;
        if (props["data-label"] !== undefined) return cell;
        return cloneElement(cellEl, {
          "data-label": toText(labels[i] ?? ""),
        });
      }),
    });
  });
  return <tbody className="divide-y divide-slate-100 lg:table-row-group">{rows}</tbody>;
}

export function Cell({
  children,
  className = "",
  ...rest
}: {
  children: ReactNode;
  className?: string;
  "data-label"?: string;
}) {
  return (
    <td
      {...rest}
    className={`block px-4 py-3 align-middle lg:table-cell lg:px-4 lg:py-2.5 ${className}`}
    >
      {children}
    </td>
  );
}

export function EmptyRow({ colSpan, message }: { colSpan: number; message: string }) {
  return (
    <tr>
      <td colSpan={colSpan} data-label="" className="px-4 py-12 text-center text-sm text-slate-500">
        {message}
      </td>
    </tr>
  );
}

export function EmptyState({
  title = "Nenhum registro encontrado",
  message = "Ajuste os filtros ou cadastre o primeiro registro.",
}: {
  title?: string;
  message?: string;
}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white px-5 py-12 text-center" role="status">
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{message}</p>
    </div>
  );
}

export function ErrorState({
  message = "Não foi possível carregar os dados.",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50/70 px-5 py-8 text-center" role="alert">
      <p className="text-sm font-semibold text-red-800">Não foi possível concluir a consulta</p>
      <p className="mt-1 text-sm text-red-700">{message}</p>
      {onRetry ? (
        <Button type="button" variant="outline" size="sm" className="mt-4 border-red-300 text-red-800 hover:bg-red-100" onClick={onRetry}>
          Tentar novamente
        </Button>
      ) : null}
    </div>
  );
}

// ------------------------------------------------------------------
// Formulário
// ------------------------------------------------------------------

export function Field({
  label,
  hint,
  children,
  className = "",
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  const fieldId = useId();
  const childId = isValidElement(children)
    ? (children.props as { id?: string }).id
    : undefined;
  const controlId = childId ?? fieldId;
  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<{ id?: string }>, {
        id: controlId,
      })
    : children;
  return (
    <div className={className}>
      <label htmlFor={controlId} className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</label>
      {control}
      {hint ? <p className="mt-1.5 text-xs leading-5 text-slate-500">{hint}</p> : null}
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 shadow-sm transition-colors focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 aria-invalid:border-red-400 aria-invalid:ring-red-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", autoComplete, spellCheck, ...props }, ref) {
    return (
      <input
        ref={ref}
        autoComplete={autoComplete ?? "off"}
        spellCheck={spellCheck ?? false}
        className={`${inputCls} ${className}`}
        {...props}
      />
    );
  }
);

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = "", ...props }, ref) {
    return <select ref={ref} className={`${inputCls} ${className}`} {...props} />;
  }
);

export function Textarea({ className = "", ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${inputCls} ${className}`} rows={3} {...props} />;
}

// ------------------------------------------------------------------
// Modal
// ------------------------------------------------------------------

export function Modal({
  open,
  title,
  onClose,
  footer,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  footer?: ReactNode;
  children?: ReactNode;
  wide?: boolean;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => !el.hasAttribute("disabled"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`flex max-h-[94dvh] w-full flex-col rounded-t-lg bg-white shadow-xl sm:rounded-lg sm:max-h-[92vh] ${
          wide ? "sm:max-w-3xl" : "sm:max-w-lg"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-3 py-3.5 sm:px-5">
          <h2 id={titleId} className="min-w-0 truncate text-base font-semibold text-gray-900">{title}</h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-auto px-3 py-4 sm:px-5">{children}</div>
        {footer ? (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 bg-slate-50/80 px-3 py-3 sm:px-5 safe-bottom">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// PageHeader
// ------------------------------------------------------------------

export function PageHeader({
  title,
  subtitle,
  contexto,
  actions,
}: {
  title: string;
  subtitle?: string;
  contexto?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        {contexto ? (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">{contexto}</p>
        ) : null}
        <h1 className="text-[1.4rem] font-bold tracking-[-0.025em] text-slate-900 sm:text-2xl">{title}</h1>
        {subtitle ? <p className="mt-1.5 max-w-3xl text-sm leading-5 text-slate-500">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}

// ------------------------------------------------------------------
// Paginacao (UX-002/006): paginação acessível e reutilizável.
// ------------------------------------------------------------------

export function Paginacao({
  total,
  pagina,
  porPagina,
  onChange,
}: {
  total: number;
  pagina: number;
  porPagina: number;
  onChange: (p: number) => void;
}) {
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  return (
    <nav aria-label="Paginação" className="flex items-center justify-between gap-3 pt-3 text-sm">
      <p className="text-xs text-slate-500" role="status">
        {total} registro(s) · página {Math.min(pagina, paginas)} de {paginas}
      </p>
      <div className="flex items-center gap-1">
        <button
          type="button"
          disabled={pagina <= 1}
          onClick={() => onChange(pagina - 1)}
          aria-label="Página anterior"
          className="rounded-md border border-slate-200 px-2.5 py-1 text-xs hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          ←
        </button>
        <button
          type="button"
          disabled={pagina >= paginas}
          onClick={() => onChange(pagina + 1)}
          aria-label="Próxima página"
          className="rounded-md border border-slate-200 px-2.5 py-1 text-xs hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          →
        </button>
      </div>
    </nav>
  );
}

// ------------------------------------------------------------------
// Loading
// ------------------------------------------------------------------

export function Loading({ message = "Carregando…" }: { message?: string }) {
  return (
    <div className="min-h-40 space-y-3 rounded-xl border border-slate-200 bg-white px-5 py-12" role="status" aria-live="polite" aria-busy="true" aria-label={message}>
      <div className="mx-auto h-3 w-40 rounded-full erp-skeleton" />
      <div className="mx-auto h-2.5 w-56 rounded-full erp-skeleton" />
      <p className="pt-1 text-center text-xs text-slate-500">{message}</p>
    </div>
  );
}
