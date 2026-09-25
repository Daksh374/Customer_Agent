import { useEffect, useRef, useState } from "react";
import { ApiError, sendChatMessage } from "../api.js";
import MessageBubble from "./MessageBubble.jsx";

const SUGGESTED_QUESTIONS = [
  "How do I reset my password?",
  "Can I get a refund on my monthly plan?",
  "How do I connect TaskFlow to Slack?",
  "You charged me twice this month!",
];

let nextId = 0;
const makeId = () => `msg-${nextId++}`;

function toAssistantMessage(data) {
  return {
    id: makeId(),
    role: "assistant",
    content: data.response,
    sources: data.retrieved_sources,
    escalate: data.escalate,
    escalationReason: data.escalation_reason,
    ticketId: data.ticket_id,
    offerEscalation: data.offer_escalation,
    offerAnswered: false,
    feedback: null,
  };
}

export default function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function sendMessage(text) {
    const message = text.trim();
    if (!message || isLoading) return;

    // Any new message answers (and hides) an open "connect to a human?" offer.
    setMessages((prev) => [
      ...prev.map((m) => (m.offerEscalation ? { ...m, offerAnswered: true } : m)),
      { id: makeId(), role: "user", content: message },
    ]);
    setInput("");
    setIsLoading(true);

    try {
      const data = await sendChatMessage(message, conversationId);
      setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, toAssistantMessage(data)]);
    } catch (err) {
      const content = err instanceof ApiError ? err.message : "Something unexpected went wrong.";
      setMessages((prev) => [...prev, { id: makeId(), role: "error", content, retryText: message }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  function retry(errorMessage) {
    // Drop the error bubble and the failed user message, then resend it.
    setMessages((prev) => prev.slice(0, prev.indexOf(errorMessage) - 1));
    sendMessage(errorMessage.retryText);
  }

  function setFeedback(messageId, value) {
    const target = messages.find((m) => m.id === messageId);
    if (!target) return;
    const next = target.feedback === value ? null : value; // clicking again clears the vote
    console.log(`[feedback] ${messageId}: ${next ?? "cleared"}`);
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback: next } : m)));
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <main className="chat-window">
      <div className="messages" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty-state">
            <h2>Hi! How can we help?</h2>
            <p>Ask anything about your TaskFlow account, billing, or integrations.</p>
            <div className="suggestions">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button key={q} className="suggestion" onClick={() => sendMessage(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            onFeedback={(value) => setFeedback(m.id, value)}
            onOfferReply={(accept) => sendMessage(accept ? "Yes, connect me to a human agent" : "No, thanks")}
            onRetry={() => retry(m)}
          />
        ))}

        {isLoading && (
          <div className="message-row assistant">
            <div className="bubble assistant typing" aria-label="Assistant is typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(input);
        }}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your question…  (Enter to send, Shift+Enter for a new line)"
          rows={1}
          maxLength={2000}
          disabled={isLoading}
          autoFocus
        />
        <button type="submit" className="button-primary" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </main>
  );
}
