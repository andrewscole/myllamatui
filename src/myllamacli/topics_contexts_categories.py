import logging

from typing import List, Dict, Optional

from myllamacli.db_models import Topic, Category
from myllamacli.prompts import ADD_TOPIC_TO_CHAT, EXISTING_CATEGORY_TO_CHAT,CREATE_NEW_CATEGORY


def create_context_dict(context_text: str) -> Dict[str, str]:
    """generate context json for upload"""

    return {"role": "system", "content": context_text}


def generate_current_topic_summary() -> List[Dict[str, str]]:
    """generate message and add to list of messages for topic summary calls"""

# get topics list
    topic_list = [topic.text for topic in Topic.select()]

    summary_specific_prompt =  f"{topic_list}."
    return {
        "role": "user",
        "content": ADD_TOPIC_TO_CHAT + summary_specific_prompt

    }


def generate_category_summary(topic_summary) -> List[Dict[str, str]]:
    """generate message and add to list of messages for topic summary calls"""

# get topics list
    category_list = [single_category.text for single_category in Category.select()]

    topic_summary_text = "This is my topic summary. " + topic_summary
    category_instructions = EXISTING_CATEGORY_TO_CHAT + f"{category_list}." + CREATE_NEW_CATEGORY

    return {
        "role": "user",
        "content": topic_summary_text + category_instructions
    }


def get_topic_list() -> None:
    """get and print a list of topics"""

    topics = Topic.select()
    for topic in topics:
        generic_print_object(topic)


def compare_topics(summary: str) -> Optional[int]:
    """compare llm generated summary to existing summaries and return mach id or None"""
    match = None
    topics = Topic.select()
    words = summary.split(" ")
    summarywords = [
        word
        for word in words
        if word.lower()
        not in ["no", "yes", "a", "the", "then", "to", "if", "or", "this", "that"]
    ]
    for word in summarywords:
        for topic in topics:
            if word.lower() in topic.text.lower():
                match = topic.id  # topic_id
    return match


def compare_topics_and_categories(summary: str, items: list) -> Optional[int]:
    """compare llm generated summary to existing summaries and return mach id or None"""
    match = None
    words = summary.split(" ")
    summarywords = [
        word
        for word in words
        if word.lower()
        not in ["no", "yes", "a", "the", "then", "to", "if", "or", "this", "that"]
    ]
    for word in summarywords:
        for item in items:
            if word.lower() in item.text.lower():
                match = item.id  # topic_id
    return match