// pages/pre-venda/data-box.tsx — card de métrica do PDV.
export function DataBox({
  label,
  value,
  largeValue = false,
  valueColor = "text-black",
}: {
  label: string;
  value?: string;
  largeValue?: boolean;
  valueColor?: string;
}) {
  return (
    <div className="flex h-full min-w-0 flex-col justify-between rounded-xl bg-white p-2 shadow-md sm:p-3">
      <span className="truncate text-xs font-bold text-gray-800 sm:text-sm">{label}</span>
      <div className={`mt-1 min-w-0 truncate text-right font-bold ${largeValue ? "text-2xl sm:text-4xl" : "text-lg sm:text-2xl"} ${valueColor}`}>{value ?? ""}</div>
    </div>
  );
}