import { useEffect, useRef, useState } from "react";
import { ApiError, sendChatMessage } from "../api.js";
import { loadChat, saveChat } from "../storage.js";
import ChatHeader from "./ChatHeader.jsx";
import Composer from "./Composer.jsx";
import { ArrowDownIcon, BotIcon } from "./Icons.jsx";
import MessageBubble from "./MessageBubble.jsx";
import WelcomeScreen from "./WelcomeScreen.jsx";

// How far from the bottom (px) still counts as "at the bottom" for auto-scroll.
const NEAR_BOTTOM_PX = 120;

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

function toAssistantMessage(data) {
  return {
    id: makeId(),
    role: "assistant",
    time: Date.now(),
    content: data.response,
    sources: data.retrieved_sources,
    escalate: data.escalate,
    escalationReason: data.escalation_reason,
    ticketId: data.ticket_id,
    offerEscalation: data.offer_escalation,
    offerAnswered: false,
  };
}

export default function ChatWindow({ onNewChat }) {
  // Restore the previous conversation (if any) so a refresh doesn't lose it.
  const [initial] = useState(loadChat);
  const [messages, setMessages] = useState(initial.messages);
  const [conversationId, setConversationId] = useState(initial.conversationId);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showJump, setShowJump] = useState(false);
  const scrollRef = useRef(null);
  // Follow new messages only while the reader is at the bottom of the chat.
  const stickToBottom = useRef(true);
  const lastScrollTop = useRef(0);

  useEffect(() => {
    saveChat(conversationId, messages);
  }, [conversationId, messages]);

  // Jump to the latest message when a saved conversation is restored.
  useEffect(() => {
    if (initial.messages.length > 0) scrollToBottom("auto");
  }, [initial]);

  // Keep up with new messages. A long answer is scrolled to its *start*, so
  // the customer reads it from the top instead of landing at its last line.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickToBottom.current || messages.length === 0) return;
    const last = messages[messages.length - 1];
    const node = last && !isLoading && el.querySelector(`[data-message-id="${last.id}"]`);
    if (node && last.role !== "user" && node.offsetHeight > el.clientHeight * 0.7) {
      node.scrollIntoView({ block: "start", behavior: "smooth" });
    } else {
      scrollToBottom();
    }
  }, [messages, isLoading]);

  function scrollToBottom(behavior = "smooth") {
    const el = scrollRef.current;
    el?.scrollTo({ top: el.scrollHeight, behavior });
  }

  function handleScroll() {
    const el = scrollRef.current;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    // Only a scroll *up* by the reader stops auto-follow; programmatic
    // scrolling always moves down, so it can't switch it off by accident.
    if (el.scrollTop < lastScrollTop.current - 4) stickToBottom.current = false;
    if (distance < NEAR_BOTTOM_PX) stickToBottom.current = true;
    lastScrollTop.current = el.scrollTop;
    setShowJump(distance > NEAR_BOTTOM_PX * 2);
  }

  async function sendMessage(text) {
    const message = text.trim();
    if (!message || isLoading) return;
    stickToBottom.current = true;

    // Any new message answers (and hides) an open "connect to a human?" offer.
    setMessages((prev) => [
      ...prev.map((m) => (m.offerEscalation ? { ...m, offerAnswered: true } : m)),
      { id: makeId(), role: "user", time: Date.now(), content: message },
    ]);
    setInput("");
    setIsLoading(true);

    try {
      const data = await sendChatMessage(message, conversationId);
      setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, toAssistantMessage(data)]);
    } catch (err) {
      const content = err instanceof ApiError ? err.message : "Something unexpected went wrong.";
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: "error", time: Date.now(), content, retryText: message },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function retry(errorMessage) {
    // Drop the error bubble and the failed user message, then resend it.
    setMessages((prev) => prev.slice(0, prev.indexOf(errorMessage) - 1));
    sendMessage(errorMessage.retryText);
  }

  return (
    <div className="chat-window">
      <ChatHeader onNewChat={onNewChat} canReset={messages.length > 0 && !isLoading} />

      <main className="messages" ref={scrollRef} onScroll={handleScroll} aria-live="polite">
        {messages.length === 0 ? (
          <WelcomeScreen onAsk={sendMessage} />
        ) : (
          <div className="message-list">
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                busy={isLoading}
                onOfferReply={(accept) => sendMessage(accept ? "Yes, connect me to a human agent" : "No, thanks")}
                onRetry={() => retry(m)}
              />
            ))}

            {isLoading && (
              <div className="message-row assistant">
                <div className="avatar" aria-hidden="true">
                  <BotIcon size={16} />
                </div>
                <div className="bubble assistant typing" role="status" aria-label="Assistant is typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {showJump && (
        <button
          type="button"
          className="jump-button"
          onClick={() => {
            stickToBottom.current = true;
            scrollToBottom();
          }}
          aria-label="Scroll to latest message"
        >
          <ArrowDownIcon size={18} />
        </button>
      )}

      <Composer value={input} onChange={setInput} onSend={() => sendMessage(input)} disabled={isLoading} />
    </div>
  );
}
