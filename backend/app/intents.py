"""Lightweight intent detection for messages that aren't support questions.

Greetings, thanks, and bare yes/no replies don't need retrieval or an LLM,
and sending them through the RAG pipeline produces odd answers (e.g. "yes"
retrieving a random article). These checks are anchored regexes: they only
match when the *whole* message is small talk, so "thanks, but where is my
refund?" still goes to the pipeline.
"""

import re

GREETING = re.compile(
    r"^(hi+|hello+|hey+|hola|namaste|good (morning|afternoon|evening))( there| team)?[\s!.,]*$",
    re.IGNORECASE,
)
THANKS = re.compile(
    r"^((ok(ay)?|great|cool|perfect)[\s,]*)?(thanks?|thank you|thx|ty)"
    r"( (so|very) much| a lot)?( for (your|the) help)?[\s!.,]*$",
    re.IGNORECASE,
)
GOODBYE = re.compile(
    r"^((ok(ay)?|thanks?)[\s,]*)?(bye|goodbye|see you|that'?s all|nothing else|"
    r"no,? that'?s (it|all))[\s!.,]*$",
    re.IGNORECASE,
)
ACKNOWLEDGEMENT = re.compile(
    r"^(ok(ay)?|cool|great|got it|alright|fine|perfect|understood|nice|noted)[\s!.,]*$",
    re.IGNORECASE,
)

# Replies to "Would you like me to connect you with a human agent?"
AFFIRMATIVE = re.compile(
    r"^\s*(yes|yeah|yep|yup|sure|ok(ay)?|please|y|definitely|of course)\b|"
    r"\bconnect me\b|\b(human|real) (agent|person)\b",
    re.IGNORECASE,
)
NEGATIVE = re.compile(r"^\s*(no|nope|nah|not now|no thanks?)\b", re.IGNORECASE)
BARE_NEGATIVE = re.compile(r"^\s*(no|nope|nah|not now|no,? thanks?|no need)[\s!.,]*$", re.IGNORECASE)

GREETING_REPLY = (
    "Hi! I'm your shopping support assistant. I can help with orders, delivery, returns, refunds, "
    "payments, coupons, and your account. What can I help you with today?"
)
THANKS_REPLY = "You're welcome! Is there anything else I can help you with?"
GOODBYE_REPLY = "Thanks for chatting with us. Have a great day!"
ACKNOWLEDGEMENT_REPLY = "Great! Let me know if there's anything else I can help you with."
DECLINE_REPLY = "No problem! Is there anything else I can help you with?"


def is_affirmative(message: str) -> bool:
    """True if the message accepts an offer (e.g. "yes", "sure, connect me")."""
    return bool(AFFIRMATIVE.search(message)) and not is_negative(message)


def is_negative(message: str) -> bool:
    """True if the message declines an offer (e.g. "no thanks")."""
    return bool(NEGATIVE.search(message))


def small_talk_reply(message: str, assistant_asked_question: bool) -> str | None:
    """Return a canned reply if the whole message is small talk, else None.

    A bare "ok" right after the assistant asked a question is an answer to
    that question, so it is left for the pipeline (and the query rewriter)
    to interpret instead of being treated as an acknowledgement.
    """
    text = message.strip()
    if GREETING.match(text):
        return GREETING_REPLY
    if THANKS.match(text):
        return THANKS_REPLY
    if GOODBYE.match(text):
        return GOODBYE_REPLY
    if BARE_NEGATIVE.match(text):
        return DECLINE_REPLY
    if ACKNOWLEDGEMENT.match(text) and not assistant_asked_question:
        return ACKNOWLEDGEMENT_REPLY
    return None
