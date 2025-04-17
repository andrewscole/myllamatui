import datetime
import logging
import json

from typing import Dict, List

from src.myllamacli.db_models import (
    Chat,
    Context,
    Topic,
    LLM_MODEL,
    CLI_Settings,
    SQLITE_DB,
)
from src.myllamacli.llm_models import get_raw_model_list

CLI_DEFAULTS = {
    "url": "http://localhost:11434",
    "context_id": 1,
    "topic_id": 1,
    "llm_model_id": 1,
}


def setup_db_and_initialize_defaults() -> None:
    """setup db and add defaults"""

    SQLITE_DB.connect()
    SQLITE_DB.create_tables([Context, Topic, Chat, LLM_MODEL, CLI_Settings])
    SQLITE_DB.close()

    # generate some defaults
    contexts_list = [
        "You are a friendly and helpful assistant, always aiming to provide informative and comprehensive answers.",
        "You are a friendly Senior Developer assisting a jounior developer by providing code examples and comprehensive explanations.",
    ]

    for context_text in contexts_list:
        context_id = Context.create(text=context_text)

    topic_text = "Dad Jokes"
    Topic.create(text=topic_text)

    read_add_models(CLI_DEFAULTS["url"])
    create_cli_defaults()


def create_temp_fake_model():
    logging.info("No Models Found. Creating a fake model. Please pull a model.")
    LLM_MODEL.create(model="Temp_fake", size=0, currently_available=True)


def read_add_models(url):
    try:
        model_list = get_raw_model_list(url)

        if len(model_list["models"]) == 0:
            create_temp_fake_model()
        else:
            for model in model_list["models"]:
                LLM_MODEL.create(
                    model=model["model"], size=model["size"], currently_available=True
                )
    except:
        create_temp_fake_model()


def create_cli_defaults():
    CLI_Settings.create(
        url=CLI_DEFAULTS["url"],
        context_id=CLI_DEFAULTS["context_id"],
        topic_id=CLI_DEFAULTS["topic_id"],
        llm_model_id=CLI_DEFAULTS["llm_model_id"],
    )


# pulls in the instance
def restore_cli_defaults(cli_settings):
    cli_settings.url = CLI_DEFAULTS["url"]
    cli_settings.topic_id = CLI_DEFAULTS["topic_id"]
    cli_settings.llm_model_id = CLI_DEFAULTS["llm_model_id"]
    cli_settings.context_id = CLI_DEFAULTS["context_id"]
    cli_settings.save()
