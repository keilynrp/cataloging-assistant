import Link from "next/link";

import { createEvidenceSession } from "./actions";

const CREATE_MESSAGES: Record<string, string> = {
  invalid: "Revisa catalogador y UUID del ítem.",
  error: "No fue posible crear la sesión de evidencia.",
  unavailable: "La creación está deshabilitada porque falta la configuración segura.",
};

export default async function EvidencePage({
  searchParams,
}: {
  searchParams: Promise<{ create?: string }>;
}) {
  const { create } = await searchParams;
  return (
    <div className="shell">
      <Link href="/" className="back-link">← Volver a registros</Link>
      <header className="profile-hero">
        <p className="eyebrow">VERTICAL-017 · evidencia externa</p>
        <h1>Nueva sesión de evidencia</h1>
        <p>
          Captura una URL como locator y/o texto aportado explícitamente. También puede crear la
          sesión vacía y adjuntar un PDF desde la página de la sesión. Este flujo crea evidencia
          local revisable y nunca escribe DSpace.
        </p>
      </header>

      {create && CREATE_MESSAGES[create] ? (
        <div className="review-status error" role="status">{CREATE_MESSAGES[create]}</div>
      ) : null}

      <form action={createEvidenceSession} className="vocabulary-form">
        <label>
          Catalogador
          <input name="created_by" minLength={2} maxLength={120} required />
        </label>
        <label>
          UUID del ítem DSpace · opcional
          <input name="item_uuid" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
        </label>
        <label className="vocabulary-wide">
          URL externa · opcional
          <input name="url" type="url" maxLength={4000} placeholder="https://…" />
        </label>
        <label className="vocabulary-wide">
          Texto de evidencia · opcional
          <textarea
            name="text"
            maxLength={250000}
            placeholder={"Puede pegar texto completo o líneas explícitas, por ejemplo:\ndc.subject.linguisticFamily: Maya"}
          />
        </label>
        <button type="submit">Crear sesión de evidencia</button>
        <small>
          El MVP no descarga la URL ni procesa archivos binarios. La fuente queda capturada con
          SHA-256 y versión del contrato maestro.
        </small>
      </form>
    </div>
  );
}
