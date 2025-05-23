import asyncio
import logging

from typing import Dict, List

from src.myllamatui.db_models import (
    Category,
    Chat,
    Context,
    Topic,
    LLM_MODEL,
    CLI_Settings,
    SQLITE_DB,
)
from src.myllamatui.llm_models import get_raw_model_list, get_model_capabilities
from src.myllamatui.widgets_and_screens.ui_widgets_messages import SupportNotifyRequest


CLI_DEFAULTS = {
    "url": "http://localhost:11434",
    "context_id": 1,
    "topic_id": 1,
    "llm_model_id": 1,
}


def initialize_db_defaults() -> None:
    """setup db and add defaults"""

    # generate some defaults
    contexts_list = [
        "You are a friendly and helpful assistant, always aiming to provide informative and comprehensive answers.",
        "You are a friendly senior developer assisting a jounior developer by providing code examples and comprehensive explanations.",
    ]

    for context_text in contexts_list:
        context_id = Context.create(text=context_text)

    category_list = [
        "default",
        "Jokes",
        "Python",
        "Ruby",
        "Software Design",
        "AWS",
        "Historical Figures",
    ]
    for category_text in category_list:
        Category.create(text=category_text)

    topic_dict = {"default": "1", "Dad Jokes": "2", "Python Textual": "3"}
    for topic_key in topic_dict.keys():
        Topic.create(text=topic_key, category_id=topic_dict[topic_key])

    CLI_Settings.create(
        url=CLI_DEFAULTS["url"],
        context_id=CLI_DEFAULTS["context_id"],
        topic_id=CLI_DEFAULTS["topic_id"],
        llm_model_id=CLI_DEFAULTS["llm_model_id"],
    )


def create_db(sqlite_database=SQLITE_DB) -> None:
    sqlite_database.connect()
    sqlite_database.create_tables(
        [Context, Category, Topic, Chat, LLM_MODEL, CLI_Settings], safe=True
    )
    sqlite_database.close()


def create_temp_fake_model() -> None:
    logging.info("No Models Found. Creating a fake model. Please pull a model.")
    SupportNotifyRequest(
        content=f"No Models Found. Creating a fake model. Please pull a model",
        severity="warning",
    )
    LLM_MODEL.create(
        model="Temp_fake", specialization="general", size=0, currently_available=True
    )


async def populate_llm_models() -> None:
    try:
        model_list = await get_raw_model_list(CLI_DEFAULTS["url"])
        if len(model_list["models"]) == 0:
            create_temp_fake_model()
        else:
            for model in model_list["models"]:
                LLM_MODEL.create(
                    model=model["model"],
                    specialization=await get_model_capabilities(
                        url, str(model["model"])
                    ),
                    size=model["size"],
                    currently_available=True,
                )
    except:
        create_temp_fake_model()
