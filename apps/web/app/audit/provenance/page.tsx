import Link from "next/link";
import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

export const dynamic = "force-dynamic";

type Audit = { actor_count: number; item_count: number; actors: Array<{
  actor_alias: string; source_field: string; confidence: number; item_count: number;
}> };

async function getAudit(): Promise<Audit | null> {
  const token = getCatalogReviewToken();
  if (!token) return null;
  const response = await fetch(`${API_URL}/api/audit/provenance-actors`, {
    headers: { "X-Catalog-Review-Token": token }, cache: "no-store",
  });
  return response.ok ? response.json() as Promise<Audit> : null;
}

export default async function ProvenanceAuditPage() {
  const audit = await getAudit();
  return <main className="shell queue-dashboard">
    <Link href="/" className="back-link">← Volver a registros</Link>
    <header className="profile-hero"><p className="eyebrow">Auditoría restringida</p><h1>Procedencia pseudonimizada</h1><p>Asociaciones derivadas de DSpace sin exponer nombres, correos ni evidencia original.</p></header>
    {!audit ? <section className="notice"><strong>Auditoría no disponible.</strong><span>Verifica la configuración segura.</span></section> : <>
      <section><div className="queue-summary"><article className="queue-metric"><p>Actores</p><strong>{audit.actor_count}</strong></article><article className="queue-metric"><p>Asociaciones</p><strong>{audit.item_count}</strong></article></div></section>
      <section><h2>Actores pseudonimizados</h2><div className="metadata-table">{audit.actors.map((actor) => <div className="metadata-row" key={actor.actor_alias}><strong>{actor.actor_alias}</strong><span>{actor.item_count} registros · {actor.source_field} · confianza {Math.round(actor.confidence * 100)}%</span></div>)}</div></section>
    </>}
    <aside className="evidence-caveat"><strong>Límite de interpretación</strong><p>Representa un depositante inferido de la procedencia, no necesariamente quien realizó la última catalogación.</p></aside>
  </main>;
}
