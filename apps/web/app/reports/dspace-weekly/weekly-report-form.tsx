"use client";

import { useState } from "react";

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const FORMATS = [
  { value: "csv", label: "Descargar CSV" },
  { value: "xlsx", label: "Descargar XLSX" },
  { value: "pdf", label: "Descargar PDF" },
] as const;

type ReportFormat = (typeof FORMATS)[number]["value"];

export function WeeklyReportForm() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState<ReportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(format: ReportFormat) {
    setError(null);
    if (!DATE_PATTERN.test(fromDate) || !DATE_PATTERN.test(toDate)) {
      setError("Selecciona las fechas inicial y final.");
      return;
    }
    if (fromDate > toDate) {
      setError("La fecha inicial no puede ser posterior a la fecha final.");
      return;
    }

    setLoading(format);
    try {
      const query = new URLSearchParams({ from: fromDate, to: toDate });
      const response = await fetch(
        `/api/reports/dspace-weekly/${format}?${query.toString()}`,
        { cache: "no-store" },
      );
      if (!response.ok) {
        setError(
          response.status === 422
            ? "El rango indicado no es válido."
            : response.status === 503
              ? "El reporte no está disponible porque falta la configuración de lectura DSpace."
              : "No fue posible generar el reporte. Inténtalo nuevamente.",
        );
        return;
      }

      const blobUrl = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = blobUrl;
      anchor.download = `dspace-weekly-${fromDate}-${toDate}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(blobUrl);
    } catch {
      setError("No fue posible conectar con el servicio de reportes.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <form className="vocabulary-form report-form" onSubmit={(event) => event.preventDefault()}>
      <label>
        Desde
        <input
          type="date"
          name="from"
          required
          value={fromDate}
          max={toDate || undefined}
          onChange={(event) => setFromDate(event.target.value)}
        />
      </label>
      <label>
        Hasta
        <input
          type="date"
          name="to"
          required
          value={toDate}
          min={fromDate || undefined}
          onChange={(event) => setToDate(event.target.value)}
        />
      </label>

      {error ? (
        <div className="review-status error vocabulary-wide" role="alert">
          {error}
        </div>
      ) : null}

      <div className="report-actions vocabulary-wide" aria-busy={loading !== null}>
        {FORMATS.map((format) => (
          <button
            type="button"
            key={format.value}
            disabled={loading !== null}
            onClick={() => download(format.value)}
          >
            {loading === format.value ? "Generando…" : format.label}
          </button>
        ))}
      </div>
      <small>
        Los tres formatos contienen exactamente las mismas siete columnas y el mismo orden de
        registros. Esta operación no modifica DSpace.
      </small>
    </form>
  );
}
