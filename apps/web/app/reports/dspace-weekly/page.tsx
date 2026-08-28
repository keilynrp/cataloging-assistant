import { WeeklyReportForm } from "./weekly-report-form";

export default function WeeklyDSpaceReportPage() {
  return (
    <div className="shell">
      <header className="profile-hero">
        <p className="eyebrow">VERTICAL-025 · operación DSpace read-only</p>
        <h1>Reporte semanal DSpace</h1>
        <p>
          Selecciona un rango inclusivo para descargar los registros YCT en CSV, XLSX o PDF.
          Las fechas se evalúan siempre en America/Mexico_City.
        </p>
      </header>
      <WeeklyReportForm />
    </div>
  );
}
