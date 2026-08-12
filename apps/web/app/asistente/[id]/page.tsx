import Link from "next/link";
import { notFound } from "next/navigation";

import { getAgentConversation } from "@/lib/api";
import { Chat } from "./chat";

export default async function AsistenteConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const conversation = await getAgentConversation(id).catch(() => null);
  if (!conversation) notFound();

  return (
    <div className="shell">
      <Link href="/asistente" className="back-link">← Nueva conversación</Link>
      <header className="profile-hero">
        <p className="eyebrow">Agente conversacional · {conversation.started_by}</p>
        <h1>Asistente de catalogación</h1>
      </header>
      <Chat conversationId={conversation.conversation_id} initialMessages={conversation.messages} />
    </div>
  );
}
