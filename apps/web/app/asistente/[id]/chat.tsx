"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import type { AgentCitation, AgentMessage } from "@/lib/api";

type Props = {
  conversationId: string;
  initialMessages: AgentMessage[];
};

type LiveMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: AgentCitation[];
  pending?: boolean;
  toolCalls?: string[];
};

function parseSseChunk(raw: string): { event: string; data: unknown } | null {
  const lines = raw.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event:"));
  const dataLine = lines.find((line) => line.startsWith("data:"));
  if (!eventLine || !dataLine) return null;
  try {
    return { event: eventLine.slice(6).trim(), data: JSON.parse(dataLine.slice(5).trim()) };
  } catch {
    return null;
  }
}

export function Chat({ conversationId, initialMessages }: Props) {
  const [messages, setMessages] = useState<LiveMessage[]>(
    initialMessages.map((message) => ({
      id: message.message_id,
      role: message.role,
      content: message.content,
      citations: message.citations,
    })),
  );
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(async () => {
    const content = input.trim();
    if (!content || busy) return;
    setInput("");
    setError(null);
    setBusy(true);

    const userId = `local-${Date.now()}`;
    const assistantId = `pending-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", content, citations: [] },
      { id: assistantId, role: "assistant", content: "", citations: [], pending: true, toolCalls: [] },
    ]);

    try {
      const response = await fetch(`/api/agent/conversations/${conversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (!response.ok || !response.body) {
        let detail = `Error del servidor (${response.status}).`;
        try {
          const body = (await response.json()) as { detail?: string };
          if (typeof body.detail === "string") detail = body.detail;
        } catch {
          // response body wasn't JSON; keep the generic status message
        }
        throw new Error(detail);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const raw of chunks) {
          const parsed = parseSseChunk(raw);
          if (!parsed) continue;
          if (parsed.event === "text_delta") {
            const { text } = parsed.data as { text: string };
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + text } : m)),
            );
          } else if (parsed.event === "tool_call") {
            const { tool } = parsed.data as { tool: string };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, toolCalls: [...(m.toolCalls ?? []), tool] } : m,
              ),
            );
          } else if (parsed.event === "done") {
            const done = parsed.data as {
              message_id: string;
              content: string;
              citations: AgentCitation[];
            };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      id: done.message_id,
                      role: "assistant",
                      content: done.content,
                      citations: done.citations,
                    }
                  : m,
              ),
            );
          } else if (parsed.event === "error") {
            const { detail } = parsed.data as { detail?: string };
            setError(detail ?? "Ocurrió un error.");
            setMessages((prev) => prev.filter((m) => m.id !== assistantId));
          }
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo contactar al agente.");
      setMessages((prev) => prev.filter((m) => m.id !== assistantId));
    } finally {
      setBusy(false);
    }
  }, [conversationId, input, busy]);

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
                  <li key={citation.target_path}>
                    <Link href={citation.target_path}>{citation.label}</Link>
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
