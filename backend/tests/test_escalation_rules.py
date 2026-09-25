import pytest

from app.escalation_rules import (
    apply_rules,
    check_frustration,
    check_sensitive_topic,
    is_affirmative,
    is_negative,
    is_shouting,
)


@pytest.mark.parametrize(
    "message",
    [
        "You charged me twice this month",
        "I want to dispute this charge",
        "My refund was denied and that's not fair",
        "I want my money back",
        "Please delete my account",
        "How do I close our workspace?",
        "I'll have my lawyer contact you",
        "I'm going to sue TaskFlow",
    ],
)
def test_sensitive_topics_escalate(message):
    assert check_sensitive_topic(message) is not None


@pytest.mark.parametrize(
    "message",
    [
        "What is your refund policy?",
        "How do I delete a task in the workspace?",
        "How do I remove a member from my workspace?",
        "How much does the Business plan cost?",
        "Can I export my data?",
    ],
)
def test_routine_questions_do_not_escalate(message):
    assert apply_rules(message, []) is None


def test_explicit_human_request_escalates():
    assert apply_rules("Can I talk to a real person please", []) is not None


def test_all_caps_is_shouting():
    assert is_shouting("WHY IS THIS STILL BROKEN")
    assert not is_shouting("Why is this broken")
    assert not is_shouting("OK")  # too short to judge


def test_strong_frustration_escalates_immediately():
    assert check_frustration("This is ridiculous, I've waited all day", []) is not None


def test_single_mild_frustration_does_not_escalate():
    assert check_frustration("Slack notifications are not working", []) is None


def test_mild_frustration_matches_contractions():
    assert check_frustration("Notifications aren't working", ["Exports don't work"]) is not None


def test_repeated_mild_frustration_escalates():
    history = ["Slack notifications are not working"]
    assert check_frustration("I already tried that, it's still not working", history) is not None


@pytest.mark.parametrize("message", ["yes", "Yes please", "sure", "ok", "Yes, connect me to a human agent"])
def test_affirmative_replies(message):
    assert is_affirmative(message)


@pytest.mark.parametrize("message", ["no", "No thanks", "nope", "not now"])
def test_negative_replies(message):
    assert is_negative(message) and not is_affirmative(message)


def test_new_question_is_neither_yes_nor_no():
    message = "How do I export my data?"
    assert not is_affirmative(message) and not is_negative(message)
