// ui/search-modal.tsx — modal de pesquisa orientado a teclado (↑/↓, ENTER, ESC).

import { useEffect, useRef, useState, type ReactNode } from "react";

export interface SearchColumn<T> {
  key: string;
  label: string;
  align?: "left" | "center" | "right";
  render?: (item: T) => ReactNode;
}

interface SearchModalProps<T> {
  open: boolean;
  title: string;
  columns: SearchColumn<T>[];
  data: T[];
  searchText?: (item: T) => string;
  extra?: ReactNode;
  onClose: () => void;
  onSelect: (item: T) => void;
}

const ALIGN: Record<"left" | "center" | "right", string> = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

export function SearchModal<T>({
  open,
  title,
  columns,
  data,
  searchText,
  extra,
  onClose,
  onSelect,
}: SearchModalProps<T>) {
  const [termo, setTermo] = useState("");
  const [sel, setSel] = useState(0);
  const selRef = useRef<HTMLDivElement>(null);

  const textoDe = (item: T): string =>
    searchText ? searchText(item) : Object.values(item as object).map((v) => String(v ?? "")).join(" ");

  const filtrado = data.filter((item) => textoDe(item).toLowerCase().includes(termo.trim().toLowerCase()));

  useEffect(() => setSel(0), [termo, data]);
  useEffect(() => {
    selRef.current?.scrollIntoView({ block: "nearest" });
  }, [sel]);

  if (!open) return null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSel((s) => Math.min(s + 1, filtrado.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSel((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && filtrado.length > 0) {
      e.preventDefault();
      onSelect(filtrado[sel]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        tabIndex={0}
        onKeyDown={handleKeyDown}
        className="flex h-[70vh] min-h-[500px] w-full max-w-4xl flex-col overflow-hidden rounded-lg bg-[#f0f0f0] shadow-2xl outline-none"
      >
        <header className="flex items-center justify-between border-b border-gray-400 bg-[#e4e4e4] px-4 py-2">
          <h2 className="text-lg font-bold text-gray-800">{title}</h2>
          <button onClick={onClose} className="px-2 text-xl font-bold leading-none text-gray-600 hover:text-red-600">
            &times;
          </button>
        </header>

        <main className="flex flex-1 flex-col gap-4 overflow-hidden bg-[#6a84a6] p-6">
          <div className="flex flex-shrink-0 flex-col rounded-xl bg-white p-3 shadow-md">
            <label className="mb-2 text-sm font-bold text-gray-800">Digite o termo da pesquisa</label>
            <input
              type="text"
              autoFocus
              autoComplete="off"
              spellCheck={false}
              value={termo}
              onChange={(e) => setTermo(e.target.value)}
              className="w-full border-b-2 border-dashed border-gray-300 bg-transparent pb-1 text-2xl font-bold text-black outline-none focus:border-blue-500"
            />
            {extra}
          </div>

          <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-gray-300 bg-white shadow-md">
            <div className="z-10 flex w-full border-b border-gray-400 bg-gray-200 p-3 text-sm font-bold uppercase text-gray-700 shadow-sm">
              {columns.map((col) => (
                <div key={col.key} className={`flex-1 truncate pr-2 ${ALIGN[col.align ?? "left"]}`}>
                  {col.label}
                </div>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto bg-white">
              {filtrado.length > 0 ? (
                filtrado.map((item, index) => {
                  const isSelected = index === sel;
                  return (
                    <div
                      key={index}
                      ref={isSelected ? selRef : null}
                      onClick={() => setSel(index)}
                      onDoubleClick={() => onSelect(item)}
                      className={`flex w-full cursor-pointer border-b border-gray-200 px-3 py-3 transition-colors ${
                        isSelected
                          ? "bg-blue-600 font-bold text-white"
                          : "text-gray-800 even:bg-gray-100 odd:bg-white hover:bg-blue-50"
                      }`}
                    >
                      {columns.map((col) => (
                        <div key={col.key} className={`flex-1 truncate pr-2 ${ALIGN[col.align ?? "left"]}`}>
                          {col.render ? col.render(item) : String((item as Record<string, unknown>)[col.key] ?? "")}
                        </div>
                      ))}
                    </div>
                  );
                })
              ) : (
                <div className="mt-8 text-center font-bold text-gray-500">Nenhum registro encontrado.</div>
              )}
            </div>
          </div>
        </main>

        <footer className="flex items-center justify-between border-t border-gray-400 bg-[#f0f0f0] p-3 text-sm font-semibold text-gray-700">
          <div className="flex items-center gap-4">
            <span>
              Navegar: <kbd className="rounded border border-gray-400 bg-white px-2 py-0.5 shadow-sm">↑</kbd>{" "}
              <kbd className="rounded border border-gray-400 bg-white px-2 py-0.5 shadow-sm">↓</kbd>
            </span>
            <span>
              Confirmar: <kbd className="rounded border border-gray-400 bg-white px-2 py-0.5 shadow-sm">ENTER</kbd>
            </span>
            <span>
              Cancelar: <kbd className="rounded border border-gray-400 bg-white px-2 py-0.5 shadow-sm">ESC</kbd>
            </span>
          </div>
          <div className="flex gap-4">
            <button onClick={onClose} className="rounded-md bg-gray-300 px-6 py-2 font-bold text-gray-800 shadow-sm hover:bg-gray-400">
              Cancelar
            </button>
            <button
              onClick={() => filtrado[sel] && onSelect(filtrado[sel])}
              className="rounded-md bg-[#6a84a6] px-6 py-2 font-bold text-white shadow-sm hover:bg-[#587291]"
            >
              Confirmar
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
