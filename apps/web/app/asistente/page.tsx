import Link from "next/link";

import { startConversation } from "./actions";

const ERROR_LABEL: Record<string, string> = {
  invalid: "El nombre debe tener entre 2 y 120 caracteres.",
  unavailable: "El agente conversacional no está configurado en este entorno.",
  error: "No se pudo iniciar la conversación. Verifica la API local y vuelve a intentarlo.",
};

export default async function AsistenteStartPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
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
    </div>
  );
}
