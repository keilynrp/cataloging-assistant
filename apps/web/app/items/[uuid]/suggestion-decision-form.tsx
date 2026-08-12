"use client";

import { useState } from "react";

import { recordSuggestionDecision } from "./actions";

export function SuggestionDecisionForm({
  itemUuid,
  suggestionId,
}: {
  itemUuid: string;
  suggestionId: string;
}) {
  const [decision, setDecision] = useState("");

  return (
    <form action={recordSuggestionDecision} className="review-form">
      <input type="hidden" name="item_uuid" value={itemUuid} />
      <input type="hidden" name="suggestion_id" value={suggestionId} />
      <label>
        Decisión
        <select
          name="decision"
          value={decision}
          onChange={(event) => setDecision(event.target.value)}
          required
        >
          <option value="" disabled>Seleccione una decisión</option>
          <option value="accepted">Aceptar y crear revisión de borrador</option>
          <option value="corrected">Corregir y crear revisión de borrador</option>
          <option value="rejected">Rechazar</option>
          <option value="deferred">Posponer</option>
        </select>
      </label>
      {decision === "corrected" ? (
        <label>
          Valor corregido
          <input name="corrected_value" maxLength={1000} required />
        </label>
      ) : null}
      <label>Revisor<input name="reviewer" minLength={2} maxLength={120} required /></label>
      <label className="review-note">
        Nota y evidencia<textarea name="note" minLength={1} maxLength={2000} required />
      </label>
      <button type="submit">Registrar decisión</button>
      <small>Aceptar o corregir crea únicamente una revisión de borrador local.</small>
    </form>
  );
}
