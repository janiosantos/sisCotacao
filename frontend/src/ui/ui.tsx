// ui/ui.tsx — componentes React + Tailwind reutilizáveis do ERP.

import {
  Children,
  cloneElement,
  forwardRef,
  isValidElement,
  useEffect,
  type ReactElement,
  type ReactNode,
} from "react";
import { X } from "lucide-react";

// ------------------------------------------------------------------
// Botão
// ------------------------------------------------------------------

type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";

const BTN_VARIANTS: Record<BtnVariant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
  secondary: "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50",
  ghost: "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
  danger: "bg-red-600 text-white hover:bg-red-700",
  outline: "border border-brand-600 text-brand-700 hover:bg-brand-50",
};

export const Button = forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: BtnVariant;
    size?: "sm" | "md";
  }
>(function Button({ children, variant = "secondary", size = "md", className = "", ...props }, ref) {
  const sizeCls = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm";
  return (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/40 disabled:opacity-50 disabled:cursor-not-allowed ${BTN_VARIANTS[variant]} ${sizeCls} ${className}`}
      {...props}
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
    <div className={`rounded-lg border border-gray-200 bg-white shadow-sm ${className}`}>
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
    <Card className={`p-4 border-l-4 ${toneCls}`}>
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${valueCls}`}>{value}</div>
      {sub ? <div className="mt-1 text-xs text-gray-500">{sub}</div> : null}
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
    gray: "bg-gray-100 text-gray-700",
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
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="mob-card w-full text-sm lg:min-w-full lg:table-fixed lg:divide-y lg:divide-gray-200">
        {rows}
      </table>
    </div>
  );
}

export function THead({ cols }: { cols: ReactNode[] }) {
  return (
    <thead className="hidden bg-gray-50 lg:table-header-group">
      <tr>
        {cols.map((c, i) => (
          <th
            key={i}
            className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
          >
            {c}
          </th>
        ))}
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
  return (
    <tbody className="divide-y divide-gray-100 lg:table-row-group">{rows}</tbody>
  );
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
      className={`block px-4 py-2.5 lg:table-cell lg:px-4 lg:py-2.5 ${className}`}
    >
      {children}
    </td>
  );
}

export function EmptyRow({ colSpan, message }: { colSpan: number; message: string }) {
  return (
    <tr>
      <td colSpan={colSpan} data-label="" className="px-4 py-10 text-center text-sm text-gray-400">
        {message}
      </td>
    </tr>
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
  return (
    <div className={className}>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      {children}
      {hint ? <p className="mt-1 text-xs text-gray-400">{hint}</p> : null}
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30";

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
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4">
      <div
        className={`flex max-h-[94dvh] w-full flex-col rounded-t-lg bg-white shadow-xl sm:rounded-lg sm:max-h-[92vh] ${
          wide ? "sm:max-w-3xl" : "sm:max-w-lg"
        }`}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-3 py-3 sm:px-5">
          <h2 className="min-w-0 truncate text-base font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-auto px-3 py-4 sm:px-5">{children}</div>
        {footer ? (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 px-3 py-3 sm:px-5 safe-bottom">
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
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-gray-500">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}

// ------------------------------------------------------------------
// Loading
// ------------------------------------------------------------------

export function Loading({ message = "Carregando…" }: { message?: string }) {
  return <div className="py-16 text-center text-sm text-gray-400">{message}</div>;
}
