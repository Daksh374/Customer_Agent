import pytest

from app.escalation_rules import (
    apply_rules,
    check_frustration,
    check_human_request,
    check_sensitive_topic,
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
        "Close my account permanently",
        "I'll have my lawyer contact you",
        "I'm going to sue you",
        "I will file a complaint in consumer court",
        "This phone is fake, not original",
        "You sent me a counterfeit watch",
    ],
)
def test_sensitive_topics_escalate(message):
    assert check_sensitive_topic(message) is not None


@pytest.mark.parametrize(
    "message",
    [
        "What is your refund policy?",
        "How do I delete an address from my account?",
        "How do I remove a saved card?",
        "How much does express delivery cost?",
        "Can I return shoes after 10 days?",
        "How do I stay safe from fraud calls?",
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
    assert check_frustration("The coupon code is not working", []) is None


def test_mild_frustration_matches_contractions():
    assert check_frustration("Coupons aren't working", ["The app doesn't work"]) is not None


def test_repeated_mild_frustration_escalates():
    history = ["The coupon code is not working"]
    assert check_frustration("I already tried that, it's still not working", history) is not None



@pytest.mark.parametrize(
    "message",
    ["connect me with a human representative.", "I want to talk to customer care", "Can I speak to an agent?",
     "Please get me a real person", "I need a callback"],
)
def test_human_requests_are_detected(message):
    assert check_human_request(message)


@pytest.mark.parametrize("message", ["How do I contact the delivery agent?", "Can I talk to the delivery agent?"])
def test_delivery_agent_is_not_a_human_request(message):
    assert check_human_request(message) is None
