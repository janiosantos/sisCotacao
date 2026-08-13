// legacy-kit.tsx — componentes e hooks para o visual "ERP legado" (Protheus).
// Replicam o padrão da pasta Padrao_Layout sem dependência de lucide-react:
// ícones são passados como ReactNode (texto/svg) pelos consumidores.

import React, { useEffect, useRef } from "react";

// ------------------------------------------------------------------
// Tokens de estilo inline (compatíveis com telas portadas)
// ------------------------------------------------------------------

export const legacyFont = '"IBM Plex Mono", Consolas, "Courier New", monospace';
export const windowShadow = "0 10px 30px rgba(0,0,0,0.45)";

export const inputStyle: React.CSSProperties = {
  fontFamily: legacyFont,
  fontSize: 12.5,
  padding: "3px 6px",
  border: "1px solid #9aa7b8",
  background: "#fff",
  color: "#22303f",
  height: 24,
  boxSizing: "border-box",
};

export const boxStyle: React.CSSProperties = {
  border: "1px solid #9aa7b8",
  background: "#fff",
};

export const boxLabelStyle: React.CSSProperties = {
  fontFamily: legacyFont,
  fontSize: 10.5,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  color: "#33404d",
  fontWeight: 700,
  marginBottom: 2,
};

// ------------------------------------------------------------------
// Atalhos (matchers)
// ------------------------------------------------------------------

export type ShortcutMatch = (e: KeyboardEvent) => boolean;

export interface Shortcut {
  match: ShortcutMatch;
  label: string;
  action: () => void;
}

export function ctrlFKey(n: number): ShortcutMatch {
  return (e) => e.ctrlKey && e.key === `F${n}`;
}

export function ctrlDigit(d: string): ShortcutMatch {
  return (e) => e.ctrlKey && !e.altKey && !e.metaKey && e.key === d;
}

export function fKey(n: number): ShortcutMatch {
  return (e) => !e.ctrlKey && !e.altKey && !e.metaKey && e.key === `F${n}`;
}

export function ctrlLetter(c: string): ShortcutMatch {
  return (e) => e.ctrlKey && e.key.toLowerCase() === c.toLowerCase();
}

// ------------------------------------------------------------------
// Hooks
// ------------------------------------------------------------------

export function useGlobalShortcuts(shortcuts: Shortcut[], enabled = true): void {
  const ref = useRef(shortcuts);
  ref.current = shortcuts;
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      for (const s of ref.current) {
        if (s.match(e)) {
          e.preventDefault();
          s.action();
          return;
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);
}

export interface LegacyFormOptions<K extends string> {
  order: readonly K[];
  modal?: boolean;
  open?: boolean;
  onClose?: () => void;
  onConfirm?: () => void;
}

export function useLegacyForm<K extends string>(opts: LegacyFormOptions<K>) {
  const refs = useRef<Record<string, HTMLElement | null>>({});
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const registerRef = (key: K) => (el: HTMLElement | null) => {
    refs.current[key] = el;
  };

  const handleEnterAsTab = (key: K) => (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const order = optsRef.current.order;
      const idx = order.indexOf(key);
      const next = order[idx + 1];
      if (next) refs.current[next]?.focus();
    }
  };

  useEffect(() => {
    if (!opts.open) return;
    const t = setTimeout(() => {
      const first = opts.order[0];
      if (first) refs.current[first]?.focus();
    }, 0);
    return () => clearTimeout(t);
  }, [opts.open, opts.order]);

  useEffect(() => {
    if (!opts.modal || !opts.open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        optsRef.current.onClose?.();
      } else if (e.ctrlKey && e.key === "F12") {
        e.preventDefault();
        optsRef.current.onConfirm?.();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [opts.modal, opts.open]);

  return { registerRef, handleEnterAsTab, refs };
}

// ------------------------------------------------------------------
// Componentes
// ------------------------------------------------------------------

export function TitleBar({
  title,
  icon,
  onClose,
}: {
  title: string;
  icon?: React.ReactNode;
  onClose?: () => void;
}) {
  return (
    <div className="lg-titlebar">
      <span className="lg-titlebar-ico">{icon ?? "▣"}</span>
      <span>{title}</span>
      <div className="lg-titlebar-actions">
        <button title="Minimizar">–</button>
        <button title="Maximizar">□</button>
        {onClose ? (
          <button title="Fechar" onClick={onClose}>
            ×
          </button>
        ) : (
          <button title="Fechar">×</button>
        )}
      </div>
    </div>
  );
}

export function SubHeader({
  title,
  meta,
}: {
  title?: React.ReactNode;
  meta?: React.ReactNode;
}) {
  return (
    <div className="lg-subheader">
      {title != null ? <span className="lg-sub-title">{title}</span> : null}
      <span className="lg-sub-meta">{meta}</span>
    </div>
  );
}

export interface SidebarAction {
  icon?: React.ReactNode;
  label: string;
  shortcut?: string;
  active?: boolean;
  onAction?: () => void;
}

export function Sidebar({
  brand,
  subBrand,
  actions,
  footerNote,
}: {
  brand?: string;
  subBrand?: string;
  actions: SidebarAction[];
  footerNote?: React.ReactNode;
}) {
  return (
    <aside className="lg-sidebar">
      {brand || subBrand ? (
        <div className="lg-sidebar-brand">
          {brand ? <b>{brand}</b> : null}
          {subBrand ? <span>{subBrand}</span> : null}
        </div>
      ) : null}
      <div className="lg-sidebar-actions">
        {actions.map((a, i) => (
          <button
            key={i}
            className={`lg-action${a.active ? " is-active" : ""}`}
            onClick={a.onAction}
          >
            {a.icon ? <span className="lg-action-ico">{a.icon}</span> : null}
            <span>{a.label}</span>
            {a.shortcut ? <span className="lg-action-shortcut">{a.shortcut}</span> : null}
          </button>
        ))}
      </div>
      {footerNote != null ? <div className="lg-sidebar-note">{footerNote}</div> : null}
    </aside>
  );
}

export function FieldBox({
  label,
  width,
  noBorderLeft,
  children,
}: {
  label?: string;
  width?: number | string;
  noBorderLeft?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div
      className="lg-fieldbox"
      style={{ width, ...(noBorderLeft ? { borderLeft: "none" } : {}) }}
    >
      {label ? <div className="lg-fieldbox-label">{label}</div> : null}
      <div className="lg-fieldbox-body">{children}</div>
    </div>
  );
}

export function LegacyModalShell({
  open,
  title,
  onClose,
  footer,
  children,
  width,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  footer?: React.ReactNode;
  children?: React.ReactNode;
  width?: number | string;
}) {
  if (!open) return null;
  return (
    <div
      className="lg-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="lg-modal" style={{ width }}>
        <TitleBar title={title} onClose={onClose} />
        <div className="lg-modal-body">{children}</div>
        {footer ? <div className="lg-modal-footer">{footer}</div> : null}
      </div>
    </div>
  );
}

export function ModalFooterButtons({
  onConfirm,
  onCancel,
  confirmRef,
  cancelRef,
  confirmTabIndex,
  cancelTabIndex,
}: {
  onConfirm: () => void;
  onCancel: () => void;
  confirmRef?: React.Ref<HTMLButtonElement>;
  cancelRef?: React.Ref<HTMLButtonElement>;
  confirmTabIndex?: number;
  cancelTabIndex?: number;
}) {
  return (
    <>
      <button ref={cancelRef} tabIndex={cancelTabIndex} className="lg-btn" onClick={onCancel}>
        Cancelar
      </button>
      <button
        ref={confirmRef}
        tabIndex={confirmTabIndex}
        className="lg-btn lg-btn--primary"
        onClick={onConfirm}
      >
        Confirmar
      </button>
    </>
  );
}
