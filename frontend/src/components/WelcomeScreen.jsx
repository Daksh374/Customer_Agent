import { CardIcon, PackageIcon, ReturnIcon, UserIcon } from "./Icons.jsx";

const TOPICS = [
  { icon: PackageIcon, title: "Orders & delivery", question: "Where is my order?" },
  { icon: ReturnIcon, title: "Returns & refunds", question: "How do I return a product?" },
  { icon: CardIcon, title: "Payments & COD", question: "My payment failed but money was deducted" },
  { icon: UserIcon, title: "Account & login", question: "I'm not getting the OTP to log in" },
];

const QUICK_QUESTIONS = [
  "How long does a refund take?",
  "My coupon code is not working",
  "Can I exchange for a different size?",
  "How do I download my invoice?",
];

export default function WelcomeScreen({ onAsk }) {
  return (
    <section className="welcome" aria-label="Get started">
      <div className="welcome-intro">
        <h2>Hi there! How can we help?</h2>
        <p>
          I can help with orders, delivery, returns, refunds, payments, and your account. Pick a
          topic or type your question below.
        </p>
      </div>

      <div className="topic-grid">
        {TOPICS.map(({ icon: TopicIcon, title, question }) => (
          <button key={title} type="button" className="topic-card" onClick={() => onAsk(question)}>
            <span className="topic-icon">
              <TopicIcon size={20} />
            </span>
            <span className="topic-title">{title}</span>
            <span className="topic-question">{question}</span>
          </button>
        ))}
      </div>

      <div className="quick-questions">
        <p className="section-label">Popular questions</p>
        <div className="chip-row">
          {QUICK_QUESTIONS.map((q) => (
            <button key={q} type="button" className="chip" onClick={() => onAsk(q)}>
              {q}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
