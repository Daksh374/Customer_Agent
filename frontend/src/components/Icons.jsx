// Small inline SVG icons (stroke-based, 24px grid) so the UI doesn't depend
// on emoji rendering, which varies across phones and operating systems.

function Icon({ children, size = 20, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export const SendIcon = (p) => (
  <Icon {...p}>
    <path d="M22 2 11 13" />
    <path d="M22 2 15 22l-4-9-9-4 20-7z" />
  </Icon>
);

export const HeadsetIcon = (p) => (
  <Icon {...p}>
    <path d="M3 14v-3a9 9 0 0 1 18 0v3" />
    <path d="M21 14v3a2 2 0 0 1-2 2h-1v-6h3zM3 14v3a2 2 0 0 0 2 2h1v-6H3z" />
    <path d="M18 19a4 4 0 0 1-4 3h-2" />
  </Icon>
);

export const NewChatIcon = (p) => (
  <Icon {...p}>
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
  </Icon>
);

export const BotIcon = (p) => (
  <Icon {...p}>
    <rect x="3" y="8" width="18" height="12" rx="3" />
    <path d="M12 8V4" />
    <circle cx="12" cy="3" r="1" />
    <path d="M8.5 14h.01M15.5 14h.01" />
  </Icon>
);

export const ChevronIcon = (p) => (
  <Icon {...p}>
    <path d="m6 9 6 6 6-6" />
  </Icon>
);

export const ArrowDownIcon = (p) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12l7 7 7-7" />
  </Icon>
);

export const TicketIcon = (p) => (
  <Icon {...p}>
    <path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4V8z" />
    <path d="M13 6v2M13 11v2M13 16v2" />
  </Icon>
);

export const AlertIcon = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4M12 16h.01" />
  </Icon>
);

export const DocIcon = (p) => (
  <Icon {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6M8 13h8M8 17h5" />
  </Icon>
);

export const PackageIcon = (p) => (
  <Icon {...p}>
    <path d="M21 8 12 3 3 8v8l9 5 9-5z" />
    <path d="m3 8 9 5 9-5M12 13v8" />
  </Icon>
);

export const ReturnIcon = (p) => (
  <Icon {...p}>
    <path d="M9 14 4 9l5-5" />
    <path d="M4 9h11a5 5 0 0 1 0 10h-3" />
  </Icon>
);

export const CardIcon = (p) => (
  <Icon {...p}>
    <rect x="2" y="5" width="20" height="14" rx="2" />
    <path d="M2 10h20M6 15h4" />
  </Icon>
);

export const UserIcon = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21a8 8 0 0 1 16 0" />
  </Icon>
);
