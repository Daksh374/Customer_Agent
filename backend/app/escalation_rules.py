"""Deterministic escalation rules.

These run before (and independently of) the LLM classifier. They're cheap,
predictable, and easy to unit test, so they handle the clear-cut cases:
sensitive topics, explicit requests for a human, and obvious frustration.
Each rule returns a human-readable reason string, or None if it doesn't fire.
"""

import re

# Topics that should always reach a human, regardless of how well the bot answers.
SENSITIVE_TOPIC_PATTERNS: dict[str, re.Pattern] = {
    "Billing dispute": re.compile(
        r"\b(dispute|chargeback|charged (me )?twice|double[- ]charged|billed (me )?twice|overcharged|"
        r"unauthori[sz]ed (charge|payment)|charged (me )?(after|without)|wrong(ly)? charged)\b",
        re.IGNORECASE,
    ),
    "Refund disagreement": re.compile(
        r"(\brefund\b.{0,60}\b(denied|rejected|refused|declined|unfair|not fair|disagree)\b)|"
        r"(\b(denied|rejected|refused|declined)\b.{0,60}\brefund\b)|"
        r"\b(want|demand|give me) my money back\b",
        re.IGNORECASE,
    ),
    # Kept tight on purpose: "delete my account" should match, but
    # "delete a task in the workspace" should not.
    "Account deletion request": re.compile(
        r"\b(delete|deleting|close|closing|erase|terminate)\s+(my|our|the|this)?\s*"
        r"(entire\s+|whole\s+|taskflow\s+)*(account|workspace)\b|"
        r"\b(delete|erase|wipe)\s+(all\s+)?(of\s+)?(my|our)\s+data\b|"
        r"\baccount deletion\b|\bright to (be forgotten|erasure)\b|\bgdpr\b",
        re.IGNORECASE,
    ),
    "Legal threat": re.compile(
        r"\b(lawyer|attorney|legal action|lawsuit|sue|suing|court|"
        r"small claims|consumer protection|report you to)\b",
        re.IGNORECASE,
    ),
}

HUMAN_REQUEST_PATTERN = re.compile(
    r"\b(speak|talk|chat|connect)\b.{0,20}\b(human|person|agent|someone|representative|manager|supervisor)\b|"
    r"\b(real|live) (person|human|agent)\b|\bescalate\b",
    re.IGNORECASE,
)

# Phrases that signal strong frustration on their own.
STRONG_FRUSTRATION_PATTERN = re.compile(
    r"\b(this is (ridiculous|absurd|unacceptable|a joke)|unacceptable|worst (service|app|support)|"
    r"(completely |totally )?useless|waste of (my )?(time|money)|fed up|sick (and tired )?of|"
    r"terrible (service|support)|pathetic|garbage)\b",
    re.IGNORECASE,
)

# Milder signals: one alone is normal, several across a conversation is not.
MILD_FRUSTRATION_PATTERN = re.compile(
    r"\b(still (not|doesn'?t|isn'?t|broken)|(not|isn'?t|aren'?t) working|(doesn'?t|don'?t) work|again\?|"
    r"not helpful|didn'?t help|annoying|frustrat\w*|already tried|keeps? (happening|failing))\b|!{2,}",
    re.IGNORECASE,
)

# Replies to "Would you like me to connect you with a human agent?"
AFFIRMATIVE_PATTERN = re.compile(
    r"^\s*(yes|yeah|yep|yup|sure|ok(ay)?|please|y|definitely|of course)\b|"
    r"\bconnect me\b|\b(human|real) (agent|person)\b",
    re.IGNORECASE,
)
NEGATIVE_PATTERN = re.compile(r"^\s*(no|nope|nah|not now|no thanks?)\b", re.IGNORECASE)

MIN_LETTERS_FOR_CAPS_CHECK = 12
CAPS_RATIO_THRESHOLD = 0.7
MILD_FRUSTRATION_LIMIT = 2


def check_sensitive_topic(message: str) -> str | None:
    """Return a reason if the message touches a topic that needs a human."""
    for label, pattern in SENSITIVE_TOPIC_PATTERNS.items():
        if pattern.search(message):
            return f"{label} — requires a human agent."
    return None


def check_human_request(message: str) -> str | None:
    """Return a reason if the customer explicitly asks for a human."""
    if HUMAN_REQUEST_PATTERN.search(message):
        return "Customer asked to speak with a human agent."
    return None


def is_shouting(message: str) -> bool:
    """True if the message is mostly upper-case letters (e.g. 'WHY IS THIS BROKEN')."""
    letters = [ch for ch in message if ch.isalpha()]
    if len(letters) < MIN_LETTERS_FOR_CAPS_CHECK:
        return False
    return sum(ch.isupper() for ch in letters) / len(letters) >= CAPS_RATIO_THRESHOLD


def count_mild_frustration(messages: list[str]) -> int:
    """Count how many of the given messages contain a mild frustration signal."""
    return sum(1 for m in messages if MILD_FRUSTRATION_PATTERN.search(m))


def check_frustration(message: str, previous_user_messages: list[str]) -> str | None:
    """Return a reason if the customer appears frustrated.

    Fires on a single strong signal (all caps, "this is ridiculous", ...) or
    on repeated mild negativity across the conversation.
    """
    if is_shouting(message):
        return "Customer appears frustrated (message written in all caps)."
    if STRONG_FRUSTRATION_PATTERN.search(message):
        return "Customer expressed strong frustration."
    if count_mild_frustration(previous_user_messages + [message]) >= MILD_FRUSTRATION_LIMIT:
        return "Repeated negative sentiment across the conversation."
    return None


def apply_rules(message: str, previous_user_messages: list[str]) -> str | None:
    """Run every rule in priority order; return the first reason that fires."""
    return (
        check_sensitive_topic(message)
        or check_human_request(message)
        or check_frustration(message, previous_user_messages)
    )


def is_affirmative(message: str) -> bool:
    """True if the message accepts an offer (e.g. "yes", "sure, connect me")."""
    return bool(AFFIRMATIVE_PATTERN.search(message)) and not is_negative(message)


def is_negative(message: str) -> bool:
    """True if the message declines an offer (e.g. "no thanks")."""
    return bool(NEGATIVE_PATTERN.search(message))
