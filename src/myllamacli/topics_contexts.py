import logging

from typing import List, Dict

from myllamacli.db_models import Topic
from myllamacli.prompts import ADD_TOPIC_TO_CHAT


def create_context_dict(context_text: str) -> Dict:
    """generate context json for upload"""

    return {"role": "system", "content": context_text}


def generate_current_topic_summary() -> List[Dict]:
    """generate message and add to list of messages for topic summary calls"""

# get topics list
    topic_list = [topic.text for topic in Topic.select()]

    summary_specific_prompt =  f"{topic_list}."
    return {
        "role": "user",
        "content": ADD_TOPIC_TO_CHAT + summary_specific_prompt

    }


def get_topic_list() -> None:
    """get and print a list of topics"""

    topics = Topic.select()
    for topic in topics:
        generic_print_object(topic)


def compare_topics(summary: str) -> int | None:
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
