import asyncio
import logging
import httpx

from typing import Dict, Any


def generate_endpoint(url: str, action: str) -> str:
    """Choose api endpoint"""

    action_dict = {
        "show_list": "tags",
        "pull": "pull",
        "model_info": "show",
        "generate": "generate",
        "delete": "delete",
        "chat": "chat",
    }
    fullurl = url + "/api/" + action_dict[action]
    return fullurl


def generate_data_for_chat(MESSAGES: list, model: str) -> Dict[str, Any]:
    """generate dict data for chat questions"""

    return {"model": model, "stream": False, "messages": MESSAGES}


# this is geared toward 1 offs not chats. Not using currently, but leaving for future
def generate_data_for_prompt(prompt_input: str, model: str) -> Dict[str, Any]:
    """generate dict data for generate file calls"""

    return {
        "model": model,
        "stream": False,
        "prompt": prompt_input,
    }


def generate_data_for_model_pull(model: str) -> Dict:
    """generate dict data for model calls"""

    return {"model": model}


def generate_input_dict(input: str) -> Dict:
    """Create input dict"""

    return {"role": "user", "content": input}


def parse_response(response_json: Dict) -> tuple[str, str]:
    """parse json data to pull out responses"""
    # messages
    logging.debug(response_json)
    if "message" in response_json.keys():
        chat_key = "message"
        answer = response_json["message"]["content"]
    # prompt
    else:
        chat_key = "response"
        answer = response_json["response"]
    return chat_key, answer


async def post_to_llm(API_ENDPOINT: str, data: dict) -> httpx.Response:
    """post call"""

    logging.debug(API_ENDPOINT)
    logging.debug(data)

    logging.info(f"Posting to API_ENDPOINT" )

    async with httpx.AsyncClient() as client:

        response = await client.post(API_ENDPOINT, json=data, timeout=300.0)

        if response.status_code != 200:
            logging.error("Call failed")

        logging.info("Call made, generating response")
        logging.debug(response)

        return response


async def get_from_llm(API_ENDPOINT: str) -> httpx.Response:
    """get call"""

    logging.debug(API_ENDPOINT)

    async with httpx.AsyncClient() as client:
        response = await client.get(API_ENDPOINT, timeout=300.0)

        if response.status_code != 200:
            logging.error("Call failed")

        logging.debug("Call made, generating response")
        logging.debug(response)

        return response


async def delete_llm_call(API_ENDPOINT: str, data: dict) -> httpx.Response:
    """delete call"""
    logging.debug(API_ENDPOINT)
    logging.debug(data)

    async with httpx.AsyncClient() as client:
        response = await client.request(method="DELETE", url=API_ENDPOINT, json=data, timeout=300.0)

        if response.status_code != 200:
            logging.error("Call failed")

        logging.debug("Call made, generating response")
        logging.debug(response)
        
        return response
