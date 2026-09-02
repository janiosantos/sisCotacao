// pages/dashboard/section.tsx — seção de card do dashboard.
export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="erp-dashboard-section">
      <div className="erp-section-heading">
        <h3>{title}</h3>
        <span>Visão detalhada</span>
      </div>
      {children}
    </section>
  );
}
