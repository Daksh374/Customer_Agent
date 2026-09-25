// Shown under an AI reply when the backend escalated the conversation.
export default function EscalationBanner({ ticketId, reason }) {
  return (
    <div className="escalation-banner" role="status">
      <span className="escalation-icon" aria-hidden="true">🧑‍💼</span>
      <div>
        <strong>
          This has been escalated to a human agent.
          {ticketId && <> Ticket {ticketId}</>}
        </strong>
        <p>A member of our support team will follow up with you shortly.</p>
        {reason && <p className="escalation-reason">Reason: {reason}</p>}
      </div>
    </div>
  );
}
