import logging
from typing import Iterator, Tuple

from src.myllamatui.db_models import Category, Context, Topic, LLM_MODEL


def model_choice_setup() -> Iterator[Tuple[str, str]]:
    return iter(
        (str(model.model), str(model.id))
        for model in LLM_MODEL.select()
        if model.currently_available == True
    )


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
