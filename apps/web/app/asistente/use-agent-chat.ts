"use client";

import { useCallback, useState } from "react";

import type { AgentCitation, AgentMessage } from "@/lib/api";

export type LiveMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: AgentCitation[];
  pending?: boolean;
  toolCalls?: string[];
};

export function toLiveMessage(message: AgentMessage): LiveMessage {
  return {
    id: message.message_id,
    role: message.role,
    content: message.content,
    citations: message.citations,
  };
}

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

/** Shared SSE-driven send/receive loop behind `/api/agent/conversations/{id}/messages`,
 * used by both the full-page chat and the floating widget so the two never drift apart. */
export function useAgentChat(conversationId: string | null, initialMessages: AgentMessage[] = []) {
  const [messages, setMessages] = useState<LiveMessage[]>(initialMessages.map(toLiveMessage));
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(async () => {
    if (!conversationId) return;
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

  return { messages, setMessages, input, setInput, busy, error, setError, send };
}
