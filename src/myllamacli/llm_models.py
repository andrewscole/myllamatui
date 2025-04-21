import logging

from typing import Dict, List

from src.myllamacli.llm_calls import (
    generate_endpoint,
    generate_data_for_model_pull,
    post_to_llm,
    get_from_llm,
    delete_llm_call,
)
from src.myllamacli.db_models import LLM_MODEL, Chat


# pulling and parsing return from Ollama
def parse_model_list(raw_model_list: Dict) -> List[str]:
    """Parse are return list of models."""

    model_list = []
    for raw_model in raw_model_list["models"]:
        model_list.append(raw_model["name"])
    return model_list


async def get_raw_model_list(url: str) -> Dict:
    """Get list of models."""

    apiendpoint = generate_endpoint(url, "show_list")
    raw_model_list = await get_from_llm(apiendpoint)
    return raw_model_list.json()


async def pull_model(url: str, model: str) -> str:
    """Pull llm model."""

    apiendpoint = generate_endpoint(url, "pull")
    data = generate_data_for_model_pull(model)
    pull_text = await post_to_llm(apiendpoint, data)
    return pull_text


async def delete_llm_model(url: str, model: str) -> str:
    """Delete llm model."""

    apiendpoint = generate_endpoint(url, "delete")
    data = generate_data_for_model_pull(model)
    delete_text = await delete_llm_call(apiendpoint, data)

    return delete_text


# checking db against Ollama
def add_model_if_not_present(ollama_list: List, stored_llm_models: List) -> None:
    """checking db against Ollama models and add if missing"""
    db_list = [llm_models.model for llm_models in stored_llm_models]

    count = 0
    for existing_model in ollama_list["models"]:
        if existing_model["model"] in db_list:
            db_model = LLM_MODEL.get(LLM_MODEL.model == existing_model["model"])
            db_model.currently_available=True
            db_model.save()

        else:
            LLM_MODEL.get_or_create(
                model=existing_model["model"],
                size=existing_model["size"],
                currently_available=True,
            )
            count += 1
            logging.debug("Adding {0} to db".format(existing_model["model"]))

    if count == 0:
        logging.debug("No new models added")


def align_db_and_ollama(raw_model_list: List, stored_llm_models: List) -> None:
    """Adjust db to reflect Ollama model state"""

    model_list = parse_model_list(raw_model_list)
    for stored_model in stored_llm_models:
        if stored_model.model in model_list:
            stored_model.currently_available = True
        else:
            stored_model.currently_available = False
        stored_model.save()
    logging.debug("Update Complete.\n")
