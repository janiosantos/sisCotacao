// pages/dashboard/section.tsx — seção de card do dashboard.
export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold text-gray-700">{title}</h3>
      {children}
    </section>
  );
}