import asyncio
import logging
import os
import re
import statistics

from datetime import datetime
from typing import List, Dict, Tuple

from src.myllamatui.db_models import Chat, Category, Topic, Context, CLI_Settings, LLM_MODEL
from src.myllamatui.topics_contexts_categories import (
    compare_topics_and_categories_prompt,
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


def save_chat(
    question: str, answer: str, context_id: str, topic_id: str, model_id: str
) -> Chat:
    """Save the current chat to the DB"""
    chat_id = Chat.create(
        question=question,
        answer=answer,
        context_id=context_id,
        topic_id=topic_id,
        llm_model_id=model_id,
    )
    logging.debug("record saved as {0}".format(chat_id))
    return chat_id


async def chat_with_llm_UI(
    url: str, question: str, context_text: str, MESSAGES: List, model_name: str
) -> Tuple[str, List]:
    """take question, context, messages, modelname and file parse for api call and return answer and messages"""

    context_dict = create_context_dict(context_text)
    user_input_dict = generate_input_dict(question)

    MESSAGES.append(context_dict)
    MESSAGES.append(user_input_dict)

    api_endpoint = generate_endpoint(url, "chat")
    data = generate_data_for_chat(MESSAGES, model_name)

    response = await post_to_llm(api_endpoint, data)
    response_json = response.json()

    answer_key, answer = parse_response(response_json)

    # append answer to messages
    MESSAGES.append(response_json[answer_key])

    logging.debug("Answer: {0}".format(answer))
    return answer, MESSAGES


async def create_content_summary(url: str, MESSAGES: list, model_name: str) -> str:
    # setup vars
    api_endpoint = generate_endpoint(url, "chat")
    data = generate_data_for_chat(MESSAGES, model_name)
    response = await post_to_llm(api_endpoint, data)
    logging.debug(response.json())
    _, topic_summary = parse_response(response.json())
    return topic_summary


async def create_and_apply_chat_topic_ui(
    url: str, chat_object_list: List, MESSAGES: List, model_name: str
) -> None:
    """Generate and update topic for the current chats"""

    summary_context = generate_current_topic_summary()
    MESSAGES.append(summary_context)

    # generate a topic summary
    topic_summary_raw = await create_content_summary(url, MESSAGES, model_name)
    topic_summary = re.sub(r"[^a-zA-Z0-9\s]", "", topic_summary_raw)
    topic_id = check_for_topic_and_category_match(topic_summary, Topic.select())

    if topic_id is None:
        # You have created a new topic, now evaluate the category for this new topic anc create if needed
        category_and_topic_summary_context = create_context_dict(
            "You are a publishing editor who creates tables of contents"
        )
        prompt = compare_topics_and_categories_prompt(topic_summary, Category.select())
        category_summary = await create_content_summary(
            url, [category_and_topic_summary_context, prompt], model_name
        )
        category_id_num = check_for_topic_and_category_match(
            category_summary, Category.select()
        )
        if category_id_num is None:
            category_id_num = Category.create(text=category_summary)
        # create new topic with new or exiting category id
        topic_id = Topic.create(text=topic_summary, category_id=category_id_num)

    return topic_id


def resume_previous_chats_ui(selected_chats: List) -> List:
    """Load Q and A from the DB onto the screen and setup abillity to continue the conversation."""

    topic_id_list = []
    context_id_list = []
    MESSAGES = []
    context_id = 1
    topic_id = 1
    for chat in selected_chats:
        topic_id_list.append(chat.topic_id)
        context_id_list.append(chat.context_id)
        MESSAGES.append(generate_input_dict(chat.question))
        MESSAGES.append({"role": "assistant", "content": chat.answer})

    if len(context_id_list) > 0:
        context_id = statistics.mode(context_id_list)
        topic_id = statistics.mode(topic_id_list)

        context_obj = Context.get_by_id(context_id)
        context_dict = create_context_dict(context_obj.text)

        MESSAGES = [context_dict] + MESSAGES
    return MESSAGES, str(topic_id)
