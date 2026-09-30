import pytest

from app.intents import (
    ACKNOWLEDGEMENT_REPLY,
    DECLINE_REPLY,
    GREETING_REPLY,
    THANKS_REPLY,
    is_affirmative,
    is_negative,
    small_talk_reply,
)


@pytest.mark.parametrize("message", ["yes", "Yes please", "sure", "ok", "Yes, connect me to a human agent"])
def test_affirmative_replies(message):
    assert is_affirmative(message)


@pytest.mark.parametrize("message", ["no", "No thanks", "nope", "not now"])
def test_negative_replies(message):
    assert is_negative(message) and not is_affirmative(message)


@pytest.mark.parametrize(
    ("message", "reply"),
    [
        ("hi", GREETING_REPLY),
        ("Hello there!", GREETING_REPLY),
        ("thanks", THANKS_REPLY),
        ("ok thank you so much", THANKS_REPLY),
        ("no thanks", DECLINE_REPLY),
        ("got it", ACKNOWLEDGEMENT_REPLY),
    ],
)
def test_small_talk_gets_canned_reply(message, reply):
    assert small_talk_reply(message, assistant_asked_question=False) == reply


@pytest.mark.parametrize(
    "message", ["hi, where is my order?", "thanks, but my refund hasn't arrived", "How do I track my order?"]
)
def test_questions_are_not_small_talk(message):
    assert small_talk_reply(message, assistant_asked_question=False) is None


def test_ok_after_a_question_is_left_for_the_pipeline():
    assert small_talk_reply("ok", assistant_asked_question=True) is None
