import Link from "next/link";

import { getAgentConversations, getAgentMetrics } from "@/lib/api";

import { startConversation } from "./actions";

const ERROR_LABEL: Record<string, string> = {
  invalid: "El nombre debe tener entre 2 y 120 caracteres.",
  unavailable: "El agente conversacional no está configurado en este entorno.",
  error: "No se pudo iniciar la conversación. Verifica la API local y vuelve a intentarlo.",
};

const STATUS_LABEL: Record<string, string> = {
  open: "Abierta",
  archived: "Archivada",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

export default async function AsistenteStartPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const [conversations, metrics] = await Promise.all([
    getAgentConversations().catch(() => null),
    getAgentMetrics().catch(() => null),
  ]);

  const summaryCards: Array<[string, string, string]> = metrics
    ? [
        ["Conversaciones", String(metrics.total_conversations), "Total registradas"],
        [
          "Mensajes por conversación",
          metrics.avg_messages_per_conversation !== null
            ? metrics.avg_messages_per_conversation.toFixed(1)
            : "—",
          "Promedio",
        ],
        [
          "Tokens acumulados",
          `${metrics.total_input_tokens.toLocaleString("es-MX")} / ${metrics.total_output_tokens.toLocaleString("es-MX")}`,
          "Entrada / salida",
        ],
        [
          "Latencia de primer fragmento",
          metrics.avg_first_chunk_latency_ms !== null
            ? `${metrics.avg_first_chunk_latency_ms} ms`
            : "—",
          "Promedio",
        ],
        [
          "Tasa de error del proveedor",
          formatPercent(metrics.turn_error_rate),
          `${metrics.turn_error_count} turno(s) fallido(s)`,
        ],
      ]
    : [];

  const toolEntries = metrics ? Object.entries(metrics.tool_calls_by_tool) : [];

  return (
    <div className="shell">
      <Link href="/" className="back-link">← Volver a registros</Link>
      <header className="profile-hero">
        <p className="eyebrow">Agente conversacional · colección piloto</p>
        <h1>Asistente de catalogación</h1>
        <p>
          Responde preguntas sobre la colección usando únicamente las herramientas internas de
          solo lectura ya construidas (búsqueda, diagnóstico, similitud, perfil, cola de trabajo,
          vocabularios). No escribe en DSpace ni genera hallazgos, borradores o sugerencias por
          su cuenta.
        </p>
      </header>
      {error ? (
        <section className="notice" role="status">
          <strong>No se pudo iniciar la conversación.</strong>
          <span>{ERROR_LABEL[error] ?? ERROR_LABEL.error}</span>
        </section>
      ) : null}
      <form className="agent-start-form" action={startConversation}>
        <label>
          Tu nombre
          <input name="started_by" placeholder="Catalogadora" minLength={2} maxLength={120} required />
        </label>
        <button type="submit">Iniciar conversación</button>
      </form>

      {conversations && conversations.length ? (
        <section aria-labelledby="recent-conversations-heading">
          <div className="section-heading">
            <h2 id="recent-conversations-heading">Conversaciones recientes</h2>
            <span>{conversations.length} mostradas</span>
          </div>
          <div className="item-list">
            {conversations.map((conversation) => (
              <Link
                className="item-card"
                href={`/asistente/${conversation.conversation_id}`}
                key={conversation.conversation_id}
              >
                <div>
                  <h3>{conversation.started_by}</h3>
                  <p>
                    {STATUS_LABEL[conversation.status] ?? conversation.status} ·{" "}
                    {conversation.message_count} mensaje(s) ·{" "}
                    {conversation.last_message_at
                      ? `última actividad ${formatDate(conversation.last_message_at)}`
                      : `iniciada ${formatDate(conversation.started_at)}`}
                  </p>
                </div>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {metrics ? (
        <section aria-labelledby="agent-metrics-heading">
          <div className="section-heading">
            <h2 id="agent-metrics-heading">Métricas operativas</h2>
            <span>{metrics.total_messages} mensajes en total</span>
          </div>
          <div className="queue-summary">
            {summaryCards.map(([label, metric, definition]) => (
              <article className="queue-metric" key={label}>
                <p>{label}</p>
                <strong>{metric}</strong>
                <small>{definition}</small>
              </article>
            ))}
          </div>
          {toolEntries.length ? (
            <div className="diagnostic-notice">
              Llamadas a herramientas:{" "}
              {toolEntries
                .sort(([, a], [, b]) => b - a)
                .map(([tool, count]) => `${tool} (${count})`)
                .join(" · ")}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
