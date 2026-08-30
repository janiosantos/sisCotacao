// pages/atualizacoes/lista-notas.tsx — lista de notas (recursos/melhorias/correções).
export function ListaNotas({
  titulo,
  cor,
  itens,
}: {
  titulo: string;
  cor: string;
  itens?: string[] | null;
}) {
  if (!itens || itens.length === 0) return null;
  return (
    <div>
      <span className={`font-semibold ${cor}`}>{titulo}:</span>
      <ul className="ml-4 list-disc">
        {itens.map((i, idx) => (
          <li key={idx}>{i}</li>
        ))}
      </ul>
    </div>
  );
}