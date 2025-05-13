import logging

from typing import List, Dict, Optional

from myllamacli.db_models import Topic, Category
from myllamacli.prompts import (
    ADD_OR_APPLY_TOPIC_TO_CHAT,
    ASSESS_SUMMARY_1,
    ASSESS_SUMMARY_2,
    ASSESS_SUMMARY_3,
    EXISTING_CATEGORY_TO_CHAT,
    CREATE_NEW_CATEGORY,
)


def create_context_dict(context_text: str) -> Dict[str, str]:
    """generate context json for upload"""

    return {"role": "system", "content": context_text}


def generate_current_topic_summary() -> List[Dict[str, str]]:
    """generate message and add to list of messages for topic summary calls"""
    topic_list = [single_topic.text for single_topic in Topic.select()]
    return {
        "role": "user",
        "content": ADD_OR_APPLY_TOPIC_TO_CHAT
        + ASSESS_SUMMARY_2
        + f"{topic_list}"
        + ASSESS_SUMMARY_2,
    }


def generate_category_summary(topic_summary) -> List[Dict[str, str]]:
    """generate message and add to list of messages for topic summary calls"""

    # get topics list
    category_list = [single_category.text for single_category in Category.select()]

    topic_summary_text = "This is my topic summary. " + topic_summary
    category_instructions = (
        EXISTING_CATEGORY_TO_CHAT + f"{category_list}." + CREATE_NEW_CATEGORY
    )

    return {"role": "user", "content": topic_summary_text + category_instructions}


#### NOTE I CAHGED THIS
def compare_topics_and_categories_prompt(
    summary: str, item_list: list
) -> Optional[int]:
    """compare llm generated summary to existing summaries and return mach id or None"""
    item_text_list = [item.text for item in item_list]
    compliation_prompt = (
        ASSESS_SUMMARY_1
        + summary
        + ASSESS_SUMMARY_2
        + f"{item_list}."
        + ASSESS_SUMMARY_3
    )
    return {"role": "user", "content": compliation_prompt}


def check_for_topic_and_category_match(summary: str, items: list) -> Optional[int]:
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
