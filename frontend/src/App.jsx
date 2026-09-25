import { useState } from "react";
import ChatWindow from "./components/ChatWindow.jsx";

export default function App() {
  // Changing the key remounts ChatWindow, which resets the conversation.
  const [chatKey, setChatKey] = useState(0);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-logo" aria-hidden="true">✓</span>
          <div>
            <h1>TaskFlow Support</h1>
            <p>AI assistant · answers from our help center</p>
          </div>
        </div>
        <button className="button-secondary" onClick={() => setChatKey((k) => k + 1)}>
          New chat
        </button>
      </header>
      <ChatWindow key={chatKey} />
    </div>
  );
}
