import asyncio
import logging
import os
import re
import statistics

from datetime import datetime
from peewee import fn
from typing import List, Dict, Tuple

from myllamacli.db_models import Chat, Topic, Context, CLI_Settings, LLM_MODEL
from myllamacli.topics_contexts import compare_topics, create_context_dict
from myllamacli.llm_calls import (
    generate_endpoint,
    generate_data_for_chat,
    generate_input_dict,
    post_to_llm,
    parse_response
)
from myllamacli.shared_utils import open_file


def save_chat(question, answer, context_id, topic_id, model_id):
    """ Save the current chat to the DB"""
    chat_id = Chat.create(
        question=question,
        answer=answer,
        context_id=context_id,
        topic_id=topic_id,
        llm_model_id=model_id,
    )
    logging.debug("record saved as {0}".format(chat_id))
    return chat_id


async def chat_with_llm_UI(url: str, 
    question: str, context_text: str, MESSAGES: List, model_name: str, file: str
) -> Tuple[str, List]:
    """ take question, context, messages, modelname and file parse for api call and return answer and messages"""

    if file != "":
        file_input = open_file(file)
        question = f"{question}. Here is my file: {file_input}"
        file = False


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


async def create_and_apply_chat_topic_ui(url: str, 
    chat_object_list: List, MESSAGES: List, model_name: str
) -> None:
    """ Generate and update topic for the current chats"""

    # setup vars
    api_endpoint = generate_endpoint(url, "chat")
    data = generate_data_for_chat(MESSAGES, model_name)
    response = await post_to_llm(api_endpoint, data)
    logging.debug(response.json())
    _, topic_summary = parse_response(response.json())

    # compare summary to existing topics
    topic_id = compare_topics(topic_summary)
    if topic_id is None:
        topic_id = Topic.create(text=topic_summary)

    # update topic_id for chats
    for current_chat in chat_object_list:
        current_chat.update_chat_topic_from_summary(topic_id)

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