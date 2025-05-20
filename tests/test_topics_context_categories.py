import pytest

from unittest.mock import patch, MagicMock
from src.myllamatui.topics_contexts_categories import (
    create_context_dict,
    generate_current_topic_summary,
    compare_topics_and_categories_prompt,
    check_for_topic_and_category_match,
)
from src.myllamatui.db_models import Topic, Category

from src.myllamatui.prompts import (
    ADD_OR_APPLY_TOPIC_TO_CHAT,
    ASSESS_SUMMARY_1,
    ASSESS_SUMMARY_2,
    ASSESS_SUMMARY_3,
    EXISTING_CATEGORY_TO_CHAT,
    CREATE_NEW_CATEGORY,
)

# Mocking database models
class Topic:
    def __init__(self, text):
        self.text = text

    @classmethod
    def select(cls):
        return [cls("Topic 1"), cls("Topic 2")]

class Category:
    def __init__(self, text):
        self.text = text

    @classmethod
    def select(cls):
        return [cls("Category 1"), cls("Category 2")]


def test_create_context_dict():
    context_text = "Hello, world!"
    result = create_context_dict(context_text)
    assert result == {"role": "system", "content": context_text}

@patch('src.myllamatui.db_models.Topic.select')
def test_generate_current_topic_summary(mock_select):
    mock_select.return_value = [Topic("Topic 1"), Topic("Topic 2")]
    summary_messages = generate_current_topic_summary()

    assert summary_messages == {"role": "user",
        "content": ADD_OR_APPLY_TOPIC_TO_CHAT
        + ASSESS_SUMMARY_2
        + f"{["Topic 1","Topic 2"]}"
        + ASSESS_SUMMARY_2,
    }

#@patch('src.myllamatui.db_models.Category.select')
#def test_generate_category_summary(mock_select):
#    mock_select.return_value = [Category("Category 1"), Category("Category 2")]
#    topic_summary = "This is a summary."
#    summary_messages = generate_category_summary(topic_summary)
#    
#    topic_summary_text = "This is my topic summary. " + topic_summary
#    category_instructions = (
#        EXISTING_CATEGORY_TO_CHAT + f"{["Category 1", "Category 2"]}." + CREATE_NEW_CATEGORY
#    )
#    
#    assert summary_messages == {"role": "user", "content": topic_summary_text + category_instructions}

def test_compare_topics_and_categories_prompt():
    summary = "This is a summary."
    topic_list = [Topic("Item 1"), Topic("Item 2")]
    result = compare_topics_and_categories_prompt(summary, topic_list)

    compliation_prompt = (
        ASSESS_SUMMARY_1
        + summary
        + ASSESS_SUMMARY_2
        + f"{topic_list}."
        + ASSESS_SUMMARY_3
    )
    expected_result =  {"role": "user", "content": compliation_prompt}
    assert result == expected_result


@pytest.mark.parametrize(
        "summary, matchid", [
            ("Existing Topic 1", 1),
            ("New Topic", None),
            ("Existing Topic 2", 2),
            ("No Match", None),
            ("Existing Topic 3", 1),  # note this will default to first match since precent is the same
            ("Existing Topic number 3", None), #precent too low
            ("No Existing Match", None), # precent too low

            ]
        )
def test_check_for_topic_and_category_match(summary, matchid):
    topic1 = Topic(text="Existing Topic 1")
    topic1.id = 1

    topic2 = Topic(text="Existing Topic 2")
    topic2.id = 2

    match = check_for_topic_and_category_match(summary, [topic1, topic2])

    assert match == matchid
