import { useEffect, useRef } from "react";
import { SendIcon } from "./Icons.jsx";

const MAX_LENGTH = 2000;
const MAX_HEIGHT_PX = 140;

export default function Composer({ value, onChange, onSend, disabled }) {
  const textareaRef = useRef(null);

  // Grow the textarea with its content, up to a limit, then scroll.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  // Return focus to the input after each reply (skipped on touch devices,
  // where focusing would pop the keyboard back up unexpectedly).
  useEffect(() => {
    if (!disabled && window.matchMedia("(hover: hover)").matches) textareaRef.current?.focus();
  }, [disabled]);

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      onSend();
    }
  }

  const canSend = !disabled && value.trim().length > 0;

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        onSend();
      }}
    >
      <div className="composer-box">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message…"
          aria-label="Type your message"
          rows={1}
          maxLength={MAX_LENGTH}
          disabled={disabled}
          enterKeyHint="send"
        />
        <button type="submit" className="send-button" disabled={!canSend} aria-label="Send message">
          <SendIcon size={18} />
        </button>
      </div>
    </form>
  );
}
