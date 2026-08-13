import Link from "next/link";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

import {
  activateProviderCredential,
  createProviderCredential,
  deactivateProviderCredential,
  deleteProviderCredential,
} from "./actions";

type ProviderCredential = {
  credential_id: string;
  provider: string;
  label: string;
  model: string;
  key_preview: string;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
};

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
};

const SAVE_MESSAGES: Record<string, string> = {
  saved: "La credencial se guardó cifrada. La API key completa no se vuelve a mostrar.",
  activated: "La credencial quedó activa; el asistente la usará en la próxima conversación.",
  deactivated: "La credencial quedó inactiva.",
  deleted: "La credencial se eliminó.",
  invalid: "Revisa los campos: proveedor, etiqueta, modelo, API key y tu nombre son obligatorios.",
  error: "No se pudo completar la operación. Intenta de nuevo.",
  unavailable: "La administración local está deshabilitada porque falta la configuración segura.",
};

async function fetchCredentials(token: string): Promise<ProviderCredential[] | null> {
  const response = await fetch(`${API_URL}/api/agent/settings/credentials`, {
    headers: { "X-Catalog-Review-Token": token },
    cache: "no-store",
  });
  if (!response.ok) return null;
  return response.json() as Promise<ProviderCredential[]>;
}

async function fetchKnownProviders(token: string): Promise<string[]> {
  const response = await fetch(`${API_URL}/api/agent/settings/providers`, {
    headers: { "X-Catalog-Review-Token": token },
    cache: "no-store",
  });
  if (!response.ok) return ["anthropic", "openai"];
  return response.json() as Promise<string[]>;
}

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ save?: string }>;
}) {
  const { save } = await searchParams;
  const token = getCatalogReviewToken();

  if (!token) {
    return (
      <div className="shell">
        <Link href="/" className="back-link">← Volver a registros</Link>
        <section className="notice" role="status">
          <strong>La administración local está deshabilitada.</strong>
          <span>
            Configura CATALOG_REVIEW_TOKEN para gestionar credenciales de proveedores de IA.
          </span>
        </section>
      </div>
    );
  }

  const [credentials, providers] = await Promise.all([
    fetchCredentials(token),
    fetchKnownProviders(token),
  ]);

  if (credentials === null) {
    return (
      <div className="shell">
        <Link href="/" className="back-link">← Volver a registros</Link>
        <section className="notice" role="status">
          <strong>No se pudieron cargar las credenciales.</strong>
          <span>Verifica que la API local esté disponible y vuelve a intentarlo.</span>
        </section>
      </div>
    );
  }

  const active = credentials.find((credential) => credential.is_active) ?? null;

  return (
    <div className="shell">
      <Link href="/" className="back-link">← Volver a registros</Link>
      {save && SAVE_MESSAGES[save] ? (
        <div
          className={
            ["saved", "activated", "deactivated", "deleted"].includes(save)
              ? "review-status"
              : "review-status error"
          }
          role="status"
        >
          {SAVE_MESSAGES[save]}
        </div>
      ) : null}
      <header className="profile-hero">
        <p className="eyebrow">Configuración · agente conversacional</p>
        <h1>Proveedores de IA</h1>
        <p>
          Administra las credenciales que usa el asistente de catalogación. Las API keys se
          cifran antes de guardarse y nunca vuelven a mostrarse completas; solo se conserva una
          vista enmascarada. Exactamente una credencial puede estar activa a la vez.
        </p>
      </header>

      <section aria-labelledby="active-provider-heading">
        <div className="section-heading">
          <h2 id="active-provider-heading">Proveedor activo</h2>
        </div>
        {active ? (
          <article className="vocabulary-card">
            <p className="eyebrow">{PROVIDER_LABELS[active.provider] ?? active.provider}</p>
            <h3>{active.label}</h3>
            <dl>
              <div><dt>Modelo</dt><dd>{active.model}</dd></div>
              <div><dt>API key</dt><dd>{active.key_preview}</dd></div>
              <div><dt>Añadida por</dt><dd>{active.created_by}</dd></div>
            </dl>
          </article>
        ) : (
          <div className="diagnostic-notice">
            No hay ninguna credencial activa. El asistente conversacional responderá con un error
            de configuración hasta que actives una.
          </div>
        )}
      </section>

      <section aria-labelledby="new-credential-heading">
        <h2 id="new-credential-heading">Añadir credencial</h2>
        <form action={createProviderCredential} className="vocabulary-form">
          <label>
            Proveedor
            <select name="provider" required>
              {providers.map((provider) => (
                <option value={provider} key={provider}>
                  {PROVIDER_LABELS[provider] ?? provider}
                </option>
              ))}
            </select>
          </label>
          <label>
            Etiqueta
            <input
              name="label"
              minLength={2}
              maxLength={120}
              placeholder="Ej. Anthropic producción"
              required
            />
          </label>
          <label>
            Modelo
            <input
              name="model"
              minLength={1}
              maxLength={120}
              placeholder="Ej. claude-sonnet-5"
              required
            />
          </label>
          <label>
            Tu nombre
            <input name="created_by" minLength={2} maxLength={120} required />
          </label>
          <label className="vocabulary-wide">
            API key
            <input
              name="api_key"
              type="password"
              minLength={8}
              maxLength={400}
              autoComplete="off"
              required
            />
          </label>
          <label>
            <input name="activate" type="checkbox" value="true" /> Activar de inmediato
          </label>
          <button type="submit">Guardar credencial</button>
          <small>
            La API key se cifra antes de guardarse en la base de datos; esta pantalla nunca la
            vuelve a mostrar completa.
          </small>
        </form>
      </section>

      {credentials.length ? (
        <section aria-labelledby="credential-list-heading">
          <h2 id="credential-list-heading">Credenciales guardadas</h2>
          <div className="vocabulary-history">
            {credentials.map((credential) => (
              <details key={credential.credential_id} open={credential.is_active}>
                <summary>
                  {credential.is_active ? "● " : ""}
                  {PROVIDER_LABELS[credential.provider] ?? credential.provider} ·{" "}
                  {credential.label}
                </summary>
                <p>{credential.model} · {credential.key_preview}</p>
                <small>Añadida por {credential.created_by}</small>
                <div className="deferred-actions">
                  {credential.is_active ? (
                    <form action={deactivateProviderCredential}>
                      <input type="hidden" name="credential_id" value={credential.credential_id} />
                      <button type="submit">Desactivar</button>
                    </form>
                  ) : (
                    <form action={activateProviderCredential}>
                      <input type="hidden" name="credential_id" value={credential.credential_id} />
                      <button type="submit">Activar</button>
                    </form>
                  )}
                  <form action={deleteProviderCredential}>
                    <input type="hidden" name="credential_id" value={credential.credential_id} />
                    <button type="submit">Eliminar</button>
                  </form>
                </div>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      <aside className="evidence-caveat">
        <strong>Límite deliberado</strong>
        <p>
          Esta pantalla nunca vuelve a mostrar una API key completa. Para rotar una credencial,
          crea una nueva y actívala; la anterior puede eliminarse después.
        </p>
      </aside>
    </div>
  );
}
