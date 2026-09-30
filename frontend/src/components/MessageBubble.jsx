import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import EscalationBanner from "./EscalationBanner.jsx";
import { AlertIcon, BotIcon } from "./Icons.jsx";
import KnowledgePanel from "./KnowledgePanel.jsx";

function formatTime(timestamp) {
  if (!timestamp) return "";
  return new Date(timestamp).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// Links in answers open in a new tab so the chat isn't lost.
// Tables scroll sideways instead of stretching the bubble on narrow screens.
const markdownComponents = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
  table: ({ node, ...props }) => (
    <div className="table-scroll">
      <table {...props} />
    </div>
  ),
};

function OfferButtons({ onReply, disabled }) {
  return (
    <div className="quick-replies" role="group" aria-label="Connect to a human agent?">
      <button type="button" className="chip primary" onClick={() => onReply(true)} disabled={disabled}>
        Yes, connect me
      </button>
      <button type="button" className="chip" onClick={() => onReply(false)} disabled={disabled}>
        No, thanks
      </button>
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div className="avatar" aria-hidden="true">
      <BotIcon size={16} />
    </div>
  );
}

export default function MessageBubble({ message, onRetry, onOfferReply, busy }) {
  if (message.role === "user") {
    return (
      <div className="message-row user" data-message-id={message.id}>
        <div className="message-stack">
          <div className="bubble user">{message.content}</div>
          <span className="meta">{formatTime(message.time)}</span>
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="message-row assistant" data-message-id={message.id}>
        <AssistantAvatar />
        <div className="message-stack">
          <div className="bubble error" role="alert">
            <AlertIcon size={18} />
            <div>
              <p>{message.content}</p>
              <button type="button" className="retry-button" onClick={onRetry} disabled={busy}>
                Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-row assistant" data-message-id={message.id}>
      <AssistantAvatar />
      <div className="message-stack">
        <div className="bubble assistant">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {message.content}
          </ReactMarkdown>
        </div>
        {message.offerEscalation && !message.offerAnswered && (
          <OfferButtons onReply={onOfferReply} disabled={busy} />
        )}
        {message.escalate && <EscalationBanner ticketId={message.ticketId} reason={message.escalationReason} />}
        <KnowledgePanel sources={message.sources} />
        <span className="meta">{formatTime(message.time)}</span>
      </div>
    </div>
  );
}
