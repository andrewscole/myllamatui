import pytest
import asyncio
import httpx

from unittest.mock import MagicMock, Mock, patch


# Import necessary modules from your application
from src.myllamatui.db_models import (
    Chat,
    Category,
    Topic,
    Context,
    CLI_Settings,
    LLM_MODEL,
)
from src.myllamatui.topics_contexts_categories import (
    check_for_topic_and_category_match,
    create_context_dict,
    generate_current_topic_summary,
)
from src.myllamatui.llm_calls import (
    generate_endpoint,
    generate_data_for_chat,
    generate_input_dict,
    post_to_llm,
    parse_response,
)
from src.myllamatui.chats import (
    save_chat,
    chat_with_llm_UI,
    create_content_summary,
    create_and_apply_chat_topic_ui,
    resume_previous_chats_ui,
    generate_topic_catgory,
    generate_chat_topic,
)


class MockTopic:
    def __init__(self, text, id):
        self.text = text
        self.id = id

    @classmethod
    def select(cls):
        return [cls("Topic 1", "1"), cls("Topic 2", "2"), cls("Topic 3", "3")]

    @classmethod
    def create(cls):
        return cls("Topic 1", "1")


class MockCategory:
    def __init__(self, text, id):
        self.text = text
        self.id = id

    @classmethod
    def select(cls):
        return [cls("Category 1", "1"), cls("Category 2", "2"), cls("Category 3", "3")]


#### passing ####
def test_save_chat(test_database):
    question = "test_question"
    answer = "test_answer"
    context_id = "1"
    topic_id = "1"
    model_id = "1"

    # Call the function
    chat_id = save_chat(question, answer, context_id, topic_id, model_id)
    this_chat = Chat.get_by_id(chat_id)
    assert this_chat.question == "test_question"
    assert this_chat.answer == "test_answer"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "returned_answer, messages_answer",
    [({"message": {"content": "42"}}, {"content": "42"}), ({"response": "42"}, "42")],
)
async def test_chat_with_llm_UI(mock_post, returned_answer, messages_answer):

    url = "http://fakeexmple.nope"

    question = "What is the meaning of life?"
    context_text = "A long context text."
    MESSAGES = []
    model_name = "fake_model"

    mock_post.return_value = httpx.Response(status_code=200, json=returned_answer)

    # Call the function
    answer, updated_messages = await chat_with_llm_UI(
        url, question, context_text, MESSAGES, model_name
    )

    mock_post.assert_called_once()
    assert answer == "42"
    assert updated_messages == [
        {"role": "system", "content": "A long context text."},
        {"role": "user", "content": "What is the meaning of life?"},
        messages_answer,
    ]


@pytest.mark.asyncio
async def test_create_content_summary(mock_post):
    url = "http://fakeexmple.nope"
    MESSAGES = [
        {"role": "system", "content": "A long context text."},
        {"role": "user", "content": "What is the meaning of life?"},
        "42",
    ]
    model_name = "gpt-3"

    # Mocking response from post_to_llm
    mock_post.return_value = httpx.Response(
        status_code=200, json={"response": "topic_summary"}
    )
    topic_summary = await create_content_summary(url, MESSAGES, model_name)

    # Assertions
    assert topic_summary == "topic_summary"
    mock_post.assert_called_once()


@pytest.mark.parametrize(
    "t_id_1, c_id_1, t_id_2, c_id_2, t_id_3, c_id_3, topic_id_result, context_text",
    [
        (2, 1, 2, 1, 3, 2, "2", "friendly and helpful"),
        (3, 2, 3, 2, 3, 2, "3", "senior developer"),
        (1, 1, 2, 1, 3, 2, "1", "friendly and helpful"),
    ],
)
def test_resume_previous_chats_ui(
    mock_chat,
    mock_context,
    t_id_1,
    c_id_1,
    t_id_2,
    c_id_2,
    t_id_3,
    c_id_3,
    topic_id_result,
    context_text,
):
    selected_chats = [
        Chat(
            question="What is your name?",
            answer="John Doe",
            context_id=c_id_1,
            topic_id=t_id_1,
        ),
        Chat(
            question="Where are you from?",
            answer="New York",
            context_id=c_id_2,
            topic_id=t_id_2,
        ),
        Chat(
            question="How many chucks can a wood chuck chuck?",
            answer="12",
            context_id=c_id_3,
            topic_id=t_id_3,
        ),
    ]

    # Call the function
    MESSAGES, topic_id = resume_previous_chats_ui(selected_chats)

    # Assertions
    assert len(MESSAGES) == 7  # Three questions and answers plus context_dict
    assert topic_id == topic_id_result
    assert context_text in MESSAGES[0]["content"]


@pytest.mark.asyncio
async def test_generate_chat_topic(mock_post):
    url = "http://fakeexmple.nope"
    model_name = "fakegpt"
    MESSAGES = ["Tell me a Joke about Godzilla!", "RAWRR I AM GODZILLA!"]

    mock_post.return_value = httpx.Response(
        status_code=200, json={"response": "Gozilla Jokes!"}
    )
    topic_summary = await generate_chat_topic(url, MESSAGES, model_name)

    assert topic_summary == "Gozilla Jokes"
    mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_generate_topic_category(mock_post):
    url = "http://fakeexmple.nope"
    model_name = "fakegpt"
    topic_summary = "Godzilla Jokes"

    mock_post.return_value = httpx.Response(status_code=200, json={"response": "Jokes"})
    category_summary = await generate_topic_catgory(url, topic_summary, model_name)

    assert category_summary == "Jokes"
    mock_post.assert_called_once()


# test topic match
@pytest.mark.asyncio
@patch("src.myllamatui.db_models.Topic.select")
async def test_create_and_apply_chat_topic_ui_topic_match(mock_select, mock_post):
    url = "http://fakeexmple.nope"
    model_name = "fakegpt"
    messages = ["Funny Jokes"]
    mock_post.return_value = httpx.Response(
        status_code=200, json={"response": "Dad Jokes"}
    )
    mock_select.return_value = [
        MockTopic(text="default", id=1),
        MockTopic(text="Dad Jokes", id=2),
        MockTopic(text="Godzilla Jokes", id=3),
    ]
    topic_id = await create_and_apply_chat_topic_ui(url, messages, model_name)

    assert topic_id == 2
    mock_post.assert_called_once()
    assert mock_select.call_count == 2


#### failing ####
# new topic and old Category
@pytest.mark.asyncio
async def test_create_and_apply_chat_topic_ui_new_topic_cat_match_name(
    mock_post, test_database
):
    url = "http://fakeexmple.nope"
    model_name = "fakegpt"
    messages = ["Funny Jokes"]
    Category.create(text="default")
    Category.create(text="Jokes")
    Category.create(text="Python")
    Topic.create(text="default", category_id="1")
    Topic.create(text="Textual Testing", category_id="2")

    mock_post.side_effect = [
        httpx.Response(status_code=200, json={"response": "Elephant Funny"}),
        httpx.Response(status_code=200, json={"response": "Jokes"}),
    ]
    topic_id = await create_and_apply_chat_topic_ui(url, messages, model_name)
    assert topic_id.id == 3
    assert mock_post.call_count == 2


# new topic and new Category
@pytest.mark.asyncio
async def test_create_and_apply_chat_topic_ui_new_topic_new_cat(
    mock_post, test_database
):
    url = "http://fakeexmple.nope"
    model_name = "fakegpt"
    messages = ["Elephants have large Trunks"]

    Category.create(text="default")
    Category.create(text="Jokes")
    Category.create(text="Python")

    Topic.create(text="default", category_id="1")
    Topic.create(text="Textual Testing", category_id="2")
    Topic.create(text="Ruby Testing", category_id="3")

    first_category_list = Category.select()
    len_first_cat_list = len(first_category_list)

    first_topic_list = Topic.select()
    len_first_topic_list = len(first_topic_list)

    len(first_topic_list)

    mock_post.side_effect = [
        httpx.Response(status_code=200, json={"response": "Elephant Trunks"}),
        httpx.Response(status_code=200, json={"response": "Elephants"}),
    ]

    topic_id = await create_and_apply_chat_topic_ui(url, messages, model_name)
    assert topic_id.id == 4
    assert str(topic_id.category_id) == str(4)
    assert mock_post.call_count == 2

    second_category_list = Category.select()
    len_second_cat_list = len(second_category_list)

    second_topic_list = Topic.select()
    len_second_top_list = len(second_topic_list)

    assert len_first_cat_list < len_second_cat_list
    assert len_first_topic_list < len_second_top_list
