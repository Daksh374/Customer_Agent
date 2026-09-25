import ReactMarkdown from "react-markdown";
import EscalationBanner from "./EscalationBanner.jsx";
import KnowledgePanel from "./KnowledgePanel.jsx";

function FeedbackButtons({ value, onFeedback }) {
  return (
    <div className="feedback" role="group" aria-label="Was this helpful?">
      <button
        className={value === "up" ? "active" : ""}
        onClick={() => onFeedback("up")}
        aria-pressed={value === "up"}
        title="Helpful"
      >
        👍
      </button>
      <button
        className={value === "down" ? "active" : ""}
        onClick={() => onFeedback("down")}
        aria-pressed={value === "down"}
        title="Not helpful"
      >
        👎
      </button>
    </div>
  );
}

function OfferButtons({ onReply }) {
  return (
    <div className="offer-actions">
      <button className="button-primary small" onClick={() => onReply(true)}>
        Yes, connect me
      </button>
      <button className="button-secondary" onClick={() => onReply(false)}>
        No, thanks
      </button>
    </div>
  );
}

export default function MessageBubble({ message, onFeedback, onRetry, onOfferReply }) {
  if (message.role === "user") {
    return (
      <div className="message-row user">
        <div className="bubble user">{message.content}</div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="message-row assistant">
        <div className="bubble error" role="alert">
          <span className="error-icon" aria-hidden="true">⚠️</span>
          <div>
            <p>{message.content}</p>
            <button className="link-button" onClick={onRetry}>
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-row assistant">
      <div className="assistant-stack">
        <div className="bubble assistant">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {message.offerEscalation && !message.offerAnswered && <OfferButtons onReply={onOfferReply} />}
        {message.escalate && (
          <EscalationBanner ticketId={message.ticketId} reason={message.escalationReason} />
        )}
        <KnowledgePanel sources={message.sources} />
        <FeedbackButtons value={message.feedback} onFeedback={onFeedback} />
      </div>
    </div>
  );
}
