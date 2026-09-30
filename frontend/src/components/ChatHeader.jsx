import { HeadsetIcon, NewChatIcon } from "./Icons.jsx";

export default function ChatHeader({ onNewChat, canReset }) {
  return (
    <header className="chat-header">
      <div className="brand">
        <div className="brand-avatar" aria-hidden="true">
          <HeadsetIcon size={20} />
        </div>
        <h1 className="brand-name">TaskFlow</h1>
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
