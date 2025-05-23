import pytest

from unittest.mock import patch, MagicMock
from src.myllamatui.topics_contexts_categories import (
    create_context_dict,
    generate_current_topic_summary,
    check_for_topic_and_category_match,
    generate_category_summary,
    category_choice_setup,
    context_choice_setup,
    topics_choice_setup,
)
from src.myllamatui.db_models import Topic, Category, Context

from src.myllamatui.prompts import (
    ADD_OR_APPLY_TOPIC_TO_CHAT,
    ASSESS_SUMMARY_1,
    ASSESS_SUMMARY_2,
    ASSESS_SUMMARY_3,
    CREATE_NEW_CATEGORY,
    CATEGORY_ASSESS,
)


# Mocking database models
class MockTopic:
    def __init__(self, text):
        self.text = text

    @classmethod
    def select(cls):
        return [cls("Topic 1"), cls("Topic 2")]

class MockContext:
    def __init__(self, text):
        self.text = text

    @classmethod
    def select(cls):
        return [cls("Context 1"), cls("Context 2")]


def test_create_context_dict():
    context_text = "Hello, world!"
    result = create_context_dict(context_text)
    assert result == {"role": "system", "content": context_text}


@patch("src.myllamatui.db_models.Topic.select")
def test_generate_current_topic_summary(mock_select):
    mock_select.return_value = [MockTopic("Topic 1"), MockTopic("Topic 2")]
    summary_messages = generate_current_topic_summary()
    assert summary_messages == {
        "role": "user",
        "content": ADD_OR_APPLY_TOPIC_TO_CHAT
        + ASSESS_SUMMARY_2
        + f"{["Topic 1","Topic 2"]}"
        + ASSESS_SUMMARY_3,
    }


@patch("src.myllamatui.db_models.Category.select")
def test_generate_category_summary(mock_category):
    category_list = ["Category 1", "Category 2"]
    mock_category.return_value = [
        Category(text="Category 1"),
        Category(text="Category 2"),
    ]
    topic_summary = "This is a summary."
    summary_messages = generate_category_summary(topic_summary)

    topic_summary_text = "This is my topic: " + topic_summary
    category_instructions = (
        CREATE_NEW_CATEGORY
        + "If the similarity between your summary "
        + ASSESS_SUMMARY_2
        + f"{category_list}"
        + CATEGORY_ASSESS
        + " Do not explain, only output 1 to 2 word category description."
    )

    assert summary_messages == {
        "role": "user",
        "content": topic_summary_text + category_instructions,
    }


# def test_generate_category_summary():
#    summary = "This is a summary."
#    topic_list = [Topic("Item 1"), Topic("Item 2")]
#    result = compare_topics_and_categories_prompt(summary, topic_list)
#
#    compliation_prompt = (
#        ASSESS_SUMMARY_1
#        + summary
#        + ASSESS_SUMMARY_2
#        + f"{topic_list}."
#        + ASSESS_SUMMARY_3
#    )
#    expected_result =  {"role": "user", "content": compliation_prompt}
#    assert result == expected_result


@pytest.mark.parametrize(
    "summary, matchid",
    [
        ("Existing Topic 1", 1),
        ("New Summary", None),
        ("Existing Topic 2", 2),
        ("No Match", None),
        (
            "Existing Topic 3",
            1,
        ),  # note this will default to first match since precent is the same
        ("New Topic number 3", None),  # precent too low
        ("No Existing summary to Match", None),  # precent too low
    ],
)
def test_check_for_topic_and_category_match(summary, matchid):
    topic1 = Topic(text="Existing Topic 1")
    topic1.id = 1

    topic2 = Topic(text="Existing Topic 2")
    topic2.id = 2

    match = check_for_topic_and_category_match(summary, [topic1, topic2])

    assert match == matchid


def test_category_choice_setup():
    mock_category = [
        MagicMock(text="default", id=1),
        MagicMock(text="Category 2", id=2),
        MagicMock(text="Category 3", id=3),
    ]

    with patch.object(Category, "select", return_value=mock_category):
        result = list(category_choice_setup())

    expected = [("Category 2", "2"), ("Category 3", "3")]
    assert result == expected


def test_topic_choice_setup():
    mock_contexts = [
        MagicMock(text="default", id=1),
        MagicMock(text="Topic 2", id=2),
        MagicMock(text="Topic 3", id=3),
    ]

    with patch.object(Topic, "select", return_value=mock_contexts):
        result = list(topics_choice_setup())

    expected = [("Topic 2", "2"), ("Topic 3", "3")]
    assert result == expected


def test_context_choice_setup():
    mock_contexts = [
        MagicMock(text="context 1", id=1),
        MagicMock(text="context 2", id=2),
        MagicMock(text="context 3", id=3),
    ]

    with patch.object(Context, "select", return_value=mock_contexts):
        result = list(context_choice_setup())

    expected = [("context 1", "1"), ("context 2", "2"), ("context 3", "3")]
    assert result == expected
