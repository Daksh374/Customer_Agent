import { HeadsetIcon, NewChatIcon } from "./Icons.jsx";

export default function ChatHeader({ onNewChat, canReset }) {
  return (
    <header className="chat-header">
      <div className="brand">
        <div className="brand-avatar" aria-hidden="true">
          <HeadsetIcon size={20} />
          <span className="status-dot" />
        </div>
        <div className="brand-text">
          <h1>Customer Support</h1>
          <p>
            <span className="status-label">Online</span> · AI assistant
          </p>
        </div>
      </div>
      <button
        type="button"
        className="header-button icon-only"
        onClick={onNewChat}
        disabled={!canReset}
        aria-label="Start a new chat"
        title="New chat"
      >
        <NewChatIcon size={18} />
      </button>
    </header>
  );
}
