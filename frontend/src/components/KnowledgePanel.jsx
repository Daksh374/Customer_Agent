import { useId, useState } from "react";
import { ChevronIcon, DocIcon } from "./Icons.jsx";

// Collapsible list of the help-center articles the answer was based on.
export default function KnowledgePanel({ sources }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  if (!sources?.length) return null;

  const label = sources.length === 1 ? "1 source" : `${sources.length} sources`;

  return (
    <div className="sources">
      <button
        type="button"
        className="sources-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={listId}
      >
        <DocIcon size={14} />
        {label}
        <ChevronIcon size={14} className={`chevron ${open ? "open" : ""}`} />
      </button>
      {open && (
        <ul className="sources-list" id={listId}>
          {sources.map((source) => (
            <li key={source.title}>
              <div className="source-title">{source.title}</div>
              <div className="source-snippet">{source.snippet}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
