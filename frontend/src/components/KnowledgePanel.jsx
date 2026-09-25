import { useState } from "react";

// Collapsible list of the help-center articles the answer was based on.
export default function KnowledgePanel({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;

  return (
    <div className="sources">
      <button className="sources-toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className={`chevron ${open ? "open" : ""}`} aria-hidden="true">▸</span>
        Sources ({sources.length})
      </button>
      {open && (
        <ul className="sources-list">
          {sources.map((source) => (
            <li key={source.title}>
              <div className="source-title">📄 {source.title}</div>
              <div className="source-snippet">{source.snippet}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
