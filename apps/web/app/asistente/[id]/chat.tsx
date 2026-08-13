"use client";

import Link from "next/link";

import type { AgentMessage } from "@/lib/api";

import { useAgentChat } from "../use-agent-chat";

type Props = {
  conversationId: string;
  initialMessages: AgentMessage[];
};

export function Chat({ conversationId, initialMessages }: Props) {
  const { messages, input, setInput, busy, error, send } = useAgentChat(
    conversationId,
    initialMessages,
  );

  return (
    <div className="agent-chat">
      <div className="agent-messages">
        {messages.map((message) => (
          <div key={message.id} className={`agent-message ${message.role}`}>
            <div className="agent-message-role">{message.role === "user" ? "Tú" : "Asistente"}</div>
            {message.pending && message.toolCalls?.length ? (
              <p className="agent-tool-indicator">Consultando: {message.toolCalls.join(", ")}</p>
            ) : null}
            <p className="agent-message-content">
              {message.content || (message.pending ? "…" : "")}
            </p>
            {message.citations.length ? (
              <ul className="agent-citations">
                {message.citations.map((citation) => (
                  <li key={`${citation.target_path}-${citation.label}`}>
                    <Link href={citation.target_path}>{citation.label}</Link>
                    {citation.detail ? <span className="agent-citation-detail"> · {citation.detail}</span> : null}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ))}
      </div>
      {error ? (
        <p className="agent-error" role="alert">
          {error}
        </p>
      ) : null}
      <form
        className="agent-input"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Pregunta sobre la colección…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          Enviar
        </button>
      </form>
      <aside className="evidence-caveat">
        <strong>Límite de interpretación</strong>
        <p>
          El asistente sólo lee evidencia local; no escribe en DSpace ni genera hallazgos,
          borradores o sugerencias por su cuenta.
        </p>
      </aside>
    </div>
  );
}
