"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { PUBLIC_API_URL } from "@/lib/api";
import type { AgentConversationDetail } from "@/lib/api";

import { toLiveMessage, useAgentChat } from "./asistente/use-agent-chat";

const STORAGE_KEY_NAME = "cat.agent.startedBy";
const STORAGE_KEY_CONVERSATION = "cat.agent.conversationId";

export function AgentWidget() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState(() =>
    typeof window === "undefined" ? "" : (localStorage.getItem(STORAGE_KEY_NAME) ?? ""),
  );
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const chat = useAgentChat(conversationId);

  useEffect(() => {
    const storedConversationId = localStorage.getItem(STORAGE_KEY_CONVERSATION);
    if (!storedConversationId) return;

    let cancelled = false;
    fetch(`${PUBLIC_API_URL}/api/agent/conversations/${storedConversationId}`, {
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error(`status ${response.status}`);
        return response.json() as Promise<AgentConversationDetail>;
      })
      .then((detail) => {
        if (cancelled) return;
        setConversationId(storedConversationId);
        chat.setMessages(detail.messages.map(toLiveMessage));
      })
      .catch(() => {
        if (cancelled) return;
        localStorage.removeItem(STORAGE_KEY_CONVERSATION);
      });
    return () => {
      cancelled = true;
    };
    // Runs once on mount; `chat.setMessages` is a stable state setter.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open]);

  const startConversation = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      const name = nameDraft.trim();
      if (name.length < 2) return;
      setCreating(true);
      setCreateError(null);
      try {
        const response = await fetch("/api/agent/conversations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ started_by: name }),
        });
        const body = await response.json().catch(() => ({}) as { detail?: string; conversation_id?: string });
        if (!response.ok) {
          throw new Error(body.detail ?? `Error del servidor (${response.status}).`);
        }
        const id = body.conversation_id as string;
        localStorage.setItem(STORAGE_KEY_NAME, name);
        localStorage.setItem(STORAGE_KEY_CONVERSATION, id);
        setConversationId(id);
      } catch (caught) {
        setCreateError(
          caught instanceof Error ? caught.message : "No se pudo iniciar la conversación.",
        );
      } finally {
        setCreating(false);
      }
    },
    [nameDraft],
  );

  const resetConversation = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY_CONVERSATION);
    setConversationId(null);
    chat.setMessages([]);
    chat.setError(null);
  }, [chat]);

  return (
    <div className="agent-widget-float" ref={rootRef}>
      <button
        type="button"
        className="agent-widget-trigger"
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="Asistente de catalogación"
        onClick={() => setOpen((value) => !value)}
      >
        <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" focusable="false">
          <path
            fill="currentColor"
            d="M12 3C7.03 3 3 6.58 3 11c0 2.39 1.19 4.53 3.08 6.02-.1.98-.5 2.19-1.4 3.48a.5.5 0 0 0 .55.77c1.86-.5 3.24-1.32 4.15-2.02.85.19 1.74.29 2.62.29 4.97 0 9-3.58 9-8s-4.03-8-9-8Z"
          />
        </svg>
      </button>
      {open ? (
        <div className="agent-widget-panel" role="dialog" aria-label="Asistente de catalogación">
          <div className="notification-panel-header">
            <strong>Asistente</strong>
            <Link
              href={conversationId ? `/asistente/${conversationId}` : "/asistente"}
              onClick={() => setOpen(false)}
            >
              Pantalla completa ↗
            </Link>
          </div>

          {!conversationId ? (
            <form className="agent-widget-start" onSubmit={startConversation}>
              <label>
                Tu nombre
                <input
                  value={nameDraft}
                  onChange={(event) => setNameDraft(event.target.value)}
                  minLength={2}
                  maxLength={120}
                  placeholder="Catalogadora"
                  required
                />
              </label>
              <button type="submit" disabled={creating}>
                Iniciar conversación
              </button>
              {createError ? (
                <p className="agent-error" role="alert">
                  {createError}
                </p>
              ) : null}
            </form>
          ) : (
            <>
              <div className="agent-messages agent-widget-messages">
                {chat.messages.length === 0 ? (
                  <p className="notification-empty">Pregunta algo sobre la colección piloto.</p>
                ) : null}
                {chat.messages.map((message) => (
                  <div key={message.id} className={`agent-message ${message.role}`}>
                    <div className="agent-message-role">
                      {message.role === "user" ? "Tú" : "Asistente"}
                    </div>
                    {message.pending && message.toolCalls?.length ? (
                      <p className="agent-tool-indicator">
                        Consultando: {message.toolCalls.join(", ")}
                      </p>
                    ) : null}
                    <p className="agent-message-content">
                      {message.content || (message.pending ? "…" : "")}
                    </p>
                    {message.citations.length ? (
                      <ul className="agent-citations">
                        {message.citations.map((citation) => (
                          <li key={`${citation.target_path}-${citation.label}`}>
                            <Link href={citation.target_path} onClick={() => setOpen(false)}>
                              {citation.label}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ))}
              </div>
              {chat.error ? (
                <p className="agent-error" role="alert">
                  {chat.error}
                </p>
              ) : null}
              <form
                className="agent-input"
                onSubmit={(event) => {
                  event.preventDefault();
                  void chat.send();
                }}
              >
                <input
                  value={chat.input}
                  onChange={(event) => chat.setInput(event.target.value)}
                  placeholder="Pregunta sobre la colección…"
                  disabled={chat.busy}
                />
                <button type="submit" disabled={chat.busy || !chat.input.trim()}>
                  Enviar
                </button>
              </form>
              <div className="notification-panel-footer">
                <button type="button" onClick={resetConversation}>
                  Nueva conversación
                </button>
              </div>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
