import Link from "next/link";

import { getItems } from "@/lib/api";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  let data: Awaited<ReturnType<typeof getItems>> | null = null;
  let unavailable = false;
  try {
    data = await getItems(q);
  } catch {
    unavailable = true;
  }

  return (
    <div className="shell">
      <section className="hero">
        <p className="eyebrow">Colección piloto · 123456789/4</p>
        <h1>Explorador de registros</h1>
        <p>
          Índice operacional derivado de DSpace. Los datos fuente se conservan sin habilitar
          modificaciones en el repositorio institucional.
        </p>
      </section>
      <p><Link href="/audit/provenance">Abrir auditoría restringida de procedencia →</Link></p>

      <form className="search" action="/">
        <label htmlFor="q">Buscar por título, handle o metadato</label>
        <div>
          <input id="q" name="q" defaultValue={q} placeholder="Ej. lengua, autoría o título" />
          <button type="submit">Buscar</button>
        </div>
      </form>

      {unavailable ? (
        <section className="notice" role="status">
          <strong>El índice local todavía no está disponible.</strong>
          <span>Inicia PostgreSQL y la API, ejecuta la sincronización y vuelve a cargar.</span>
        </section>
      ) : (
        <section aria-labelledby="results-heading">
          <div className="section-heading">
            <h2 id="results-heading">Registros</h2>
            <span>{data?.total ?? 0} resultados</span>
          </div>
          <div className="item-list">
            {data?.items.map((item) => (
              <Link className="item-card" href={`/items/${item.uuid}`} key={item.uuid}>
                <div>
                  <h3>{item.name}</h3>
                  <p>{item.handle ?? item.uuid}</p>
                </div>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
