// pages/pre-venda/linha-info.tsx — linha rótulo/valor de detalhe.
export function LinhaInfo({ label, valor }: { label: string; valor?: string | null }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-xs font-medium uppercase text-gray-500">{label}</span>
      <span className="text-right font-medium text-gray-800">{valor || "—"}</span>
    </div>
  );
}