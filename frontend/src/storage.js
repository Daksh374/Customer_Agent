// Persists the open conversation in localStorage so a page refresh doesn't
// lose the chat. Storage can be unavailable (private mode, blocked site
// data), so every access is wrapped and failures fall back to a fresh chat.

const STORAGE_KEY = "support-chat-v1";

export function loadChat() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && Array.isArray(saved.messages)) return saved;
  } catch {
    // Corrupt or inaccessible storage: start fresh.
  }
  return { conversationId: null, messages: [] };
}

export function saveChat(conversationId, messages) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ conversationId, messages }));
  } catch {
    // Quota exceeded or storage blocked: the chat still works, it just won't survive a refresh.
  }
}

export function clearChat() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to clear.
  }
}
