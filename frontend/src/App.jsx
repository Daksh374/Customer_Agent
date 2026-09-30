import { useState } from "react";
import ChatWindow from "./components/ChatWindow.jsx";
import { clearChat } from "./storage.js";

export default function App() {
  // Changing the key remounts ChatWindow, which starts a fresh conversation.
  const [chatKey, setChatKey] = useState(0);

  function startNewChat() {
    clearChat();
    setChatKey((k) => k + 1);
  }

  return (
    <div className="app-shell">
      <ChatWindow key={chatKey} onNewChat={startNewChat} />
    </div>
  );
}
