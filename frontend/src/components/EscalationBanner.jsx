import { TicketIcon } from "./Icons.jsx";

// Shown under an AI reply when the conversation was handed to a human agent.
export default function EscalationBanner({ ticketId, reason }) {
  return (
    <div className="escalation-card" role="status">
      <div className="escalation-icon">
        <TicketIcon size={18} />
      </div>
      <div className="escalation-body">
        <div className="escalation-title">
          Escalated to a human agent
          {ticketId && <span className="ticket-badge">Ticket {ticketId}</span>}
        </div>
        <p>Our support team will review this conversation and follow up with you shortly.</p>
        {reason && <p className="escalation-reason">Reason: {reason}</p>}
      </div>
    </div>
  );
}
