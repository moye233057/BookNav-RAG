import type { ChatMessage } from "./App";

type ThreadProps = {
  messages: ChatMessage[];
  isAsking: boolean;
  activeReplyId: string | null;
  onShowSources: (replyId: string) => void;
};

type ThreadMessageProps = {
  message: ChatMessage;
  activeReplyId: string | null;
  onShowSources: (replyId: string) => void;
};

function ThreadMessage({ message, activeReplyId, onShowSources }: ThreadMessageProps) {
  switch (message.kind) {
    case "user":
      return (
        <article className="bubble bubble-user">
          <p>{message.text}</p>
        </article>
      );
    case "assistant":
      return (
        <div className="reply-row">
          <article className="bubble bubble-assistant">
            <p className="answer">{message.answer}</p>
          </article>
          <button
            type="button"
            className="sources-button"
            aria-pressed={activeReplyId === message.id}
            onClick={() => onShowSources(message.id)}
          >
            参考资料
          </button>
        </div>
      );
    case "error":
      return (
        <article className="bubble bubble-error">
          <p>{message.message}</p>
        </article>
      );
    default: {
      const _: never = message;
      return _;
    }
  }
}

export function Thread({ messages, isAsking, activeReplyId, onShowSources }: ThreadProps) {
  const empty = messages.length === 0 && !isAsking;
  return (
    <section className="thread" aria-label="对话">
      <div className="thread-body">
        {empty ? <p className="empty">还没有提问。例如：后视镜怎么折叠</p> : null}
        {messages.map((message) => (
          <ThreadMessage
            key={message.id}
            message={message}
            activeReplyId={activeReplyId}
            onShowSources={onShowSources}
          />
        ))}
        {isAsking ? <p className="status">正在检索并生成…</p> : null}
      </div>
    </section>
  );
}
