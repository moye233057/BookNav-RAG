import { useState } from "react";
import { askQuestion } from "./api";
import type { Citation, FilterTag, GenerationResult } from "./api";
import { Composer } from "./Composer";
import { Sources } from "./Sources";
import { Thread } from "./Thread";

export type UserMessage = {
  kind: "user";
  id: string;
  text: string;
};

export type AssistantMessage = {
  kind: "assistant";
  id: string;
  answer: string;
  citations: Citation[];
  tags: FilterTag[];
};

export type ErrorMessage = {
  kind: "error";
  id: string;
  message: string;
};

export type ChatMessage = UserMessage | AssistantMessage | ErrorMessage;

function nextId(prefix: string, serial: number): string {
  return `${prefix}-${serial}`;
}

function assistantById(messages: ChatMessage[], replyId: string | null): AssistantMessage | null {
  if (replyId === null) {
    return null;
  }
  const row = messages.find((message) => message.id === replyId);
  if (row === undefined || row.kind !== "assistant") {
    return null;
  }
  return row;
}

export function App() {
  const [session] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [serial, setSerial] = useState(1);
  const [activeReplyId, setActiveReplyId] = useState<string | null>(null);

  async function onSubmit() {
    const text = draft.trim();
    if (!text || isAsking) {
      return;
    }
    const userId = nextId("user", serial);
    const replyId = nextId("reply", serial);
    setSerial(serial + 1);
    setDraft("");
    setMessages((current) => [...current, { kind: "user", id: userId, text }]);
    setIsAsking(true);
    try {
      const result: GenerationResult = await askQuestion({
        text,
        session,
      });
      const assistant: AssistantMessage = {
        kind: "assistant",
        id: replyId,
        answer: result.answer,
        citations: result.citations,
        tags: result.tags,
      };
      setMessages((current) => [...current, assistant]);
      setActiveReplyId(replyId);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "提问失败";
      const errorRow: ErrorMessage = { kind: "error", id: replyId, message };
      setMessages((current) => [...current, errorRow]);
    } finally {
      setIsAsking(false);
    }
  }

  const activeReply = assistantById(messages, activeReplyId);

  return (
    <div className="layout">
      <header className="topbar">
        <h1>知识库问答</h1>
        <p>问知识库里的内容。点答案旁的参考资料查看该次检索。</p>
      </header>
      <div className="main">
        <Thread
          messages={messages}
          isAsking={isAsking}
          activeReplyId={activeReplyId}
          onShowSources={setActiveReplyId}
        />
        <Composer
          draft={draft}
          tags={activeReply === null ? [] : activeReply.tags}
          isAsking={isAsking}
          onDraftChange={setDraft}
          onSubmit={onSubmit}
        />
      </div>
      <Sources citations={activeReply === null ? [] : activeReply.citations} />
    </div>
  );
}
