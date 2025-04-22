import logging

from typing import List, Dict

from myllamacli.db_models import Topic


def create_context_dict(context_text: str) -> Dict:
    """generate context json for upload"""

    return {"role": "system", "content": context_text}


def generate_current_topic_summary() -> List[Dict]:
    """generate message and add to list of messages for topic summary calls"""

    topics = Topic.select()
    topics_list = [topic.text for topic in topics]
    return {
        "role": "user",
        "content": f"Create a concise topic description about the current conversation. \
            Use as few words as possible, ideally 2 or 3 words. \
            This should be concise like a bullet point in presentiation, but should contain no symbols. \
            Only crete a new topic summary if there is not an obvious match with a previous summary here: {topics_list}. \
            If this is about code, include the language, framework that is discussed, or both."
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
