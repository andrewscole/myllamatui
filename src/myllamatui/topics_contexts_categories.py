import logging

from typing import Dict, Iterator, List, Optional, Tuple

from src.myllamatui.db_models import Topic, Category, Context
from src.myllamatui.prompts import (
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


#### pulling out here and in tests. Currently unused. Not fully deleting yet.
# def generate_category_summary(topic_summary) -> List[Dict[str, str]]:
#    """generate message and add to list of messages for topic summary calls"""
#
#    # get topics list
#    category_list = [single_category.text for single_category in Category.select()]
#
#    topic_summary_text = "This is my topic summary. " + topic_summary
#    category_instructions = (
#        EXISTING_CATEGORY_TO_CHAT + f"{category_list}." + CREATE_NEW_CATEGORY
#    )
#
#    return {"role": "user", "content": topic_summary_text + category_instructions}


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
    selected_match = None
    words = summary.split(" ")

    # filter for non-essential words
    summarywords = [
        word
        for word in words
        if word.lower()
        not in ["no", "yes", "a", "the", "then", "to", "if", "or", "this", "that", "is"]
    ]

    # loop through remaining words and find matches in existing topics.
    # create a dict withthe {topic_id:num of matches}
    match_dict = {}
    for i in range(len(summarywords)):
        word = summarywords[i]
        for item in items:
            if word.lower() in item.text.lower():
                match = item.id  # topic_id
                if match in match_dict.keys():
                    match_dict[match] += 1
                else:
                    match_dict[match] = 1

    # find the highest match in the dict from above
    # if above 60% of the essential words match an exisiting topic, use it
    highest = 0
    for id in match_dict.keys():
        if match_dict[id] > highest:
            highest = match_dict[id]
            potential_selection = id
    if highest / len(summarywords) > 0.5:
        selected_match = potential_selection

    return selected_match


# defs for returing items to ui sepcifically
def context_choice_setup() -> Iterator[Tuple[str, str]]:
    return iter((str(context.text), str(context.id)) for context in Context.select())


def category_choice_setup() -> Iterator[Tuple[str, str]]:
    return iter(
        (str(category.text), str(category.id))
        for category in Category.select()
        if category.id > 1
    )


def topics_choice_setup() -> Iterator[Tuple[str, str]]:
    return iter(
        (str(topic.text), str(topic.id))
        for topic in Topic.select()
        if topic.text != "default"
    )
