import asyncio
import logging
import os
import re
import statistics

from datetime import datetime
from peewee import fn
from typing import List, Dict, Tuple

from src.myllamacli.db_models import Chat, Topic, Context, CLI_Settings, LLM_MODEL
from myllamacli.topics_contexts import compare_topics, create_context_dict
from src.myllamacli.llm_calls import (
    generate_endpoint,
    generate_data_for_chat,
    post_to_llm,
    generate_data_for_prompt,
)
from src.myllamacli.shared_utils import open_file


def generate_input_dict(input: str) -> Dict:
    """Create input dict"""

    return {"role": "user", "content": input}


def parse_answers(response_json: Dict) -> tuple[str, str]:
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

def parse_export_path(export_path: str, is_dir: bool = False) -> str:
    """Parse the export path"""

    if "." in export_path and is_dir == True:
        export_path = input("Please input a path to a folder only:\n")

    if "~" in export_path:
        home = os.path.expanduser("~")
        split_path = export_path.split("~")
        export_path = home + split_path[1]
    return export_path


def export_text_file(export_path: str, chats: list) -> None:
    """Export a chat session or topic to a file"""
    logging.debug("chats at the export stage")
    logging.debug(chats)

    with open(export_path, "w") as file:
        for i in range(0, len(chats)):
            file.write(f"Chat #:{i + 1}" + "\n")
            file.write("Question:" + "\n")
            file.write(chats[i].question)
            file.write("\n" + "Answer:" + "\n")
            file.write(chats[i].answer)
            if i < len(chats) - 1:
                file.write("\n" + "---------------" + "\n")


def export_code_file(export_path: str, chats: list) -> None:
    """Export code sections to individual files."""

    logging.info(
        "This exports code only. To capture the entire chat, print to chat.\nThis will only export matches longer than 7 lines."
    )
    match_dict = {
        "bash": ".sh",
        "c": ".c", 
        "c++": ".cpp",
        "headers": ".h",
        "python": ".py", 
        "ruby": ".rb", 
        "ini": ".ini", 
        "go": ".go",
        "rust": "rs",
        "javascript": ".js",
        "json": ".json",
        "css": ".css",
        "textualcss": ".tcss",
        "yaml": ".yaml", 
        "xml": ".xml",
        "toml": ".toml",
        "text": ".txt",
    }
    
    
    #match_list = ["python", "ruby", "ini", "bash", "go", "rust", "pearl", ]

    # ensure path exists: 
    if not os.path.exists(export_path):
        logging.info("creating: {0}".format(export_path))
        os.mkdir(export_path)

    logging.info("length of chats: {0}".format(len(chats)))
    logging.info(chats[0].id)
    for i in range(0, len(chats)):
        chat = chats[i]
        logging.info(chat)
        file_count = 1
        #single_chat = chat.answer
        #logging.info(single_chat)
        # each comlete occurance will be broken in to a item in list
        pattern = re.compile(r"```\w.*?```", re.MULTILINE | re.DOTALL)
        matches = re.findall(pattern, chat.answer)

        for match in matches:
            # now look at the individual items in each "file" in a list
            # this gives you lists in the list essentially
            lines = match.splitlines(keepends=True)
            # if less than 8 ignore (you can copy it)
            if len(lines) < 7:
                pass
            else:
                # if more than 8 match the type and create file names
                for language_match in match_dict.keys():
                    if language_match in lines[0]:
                        ### SO right now this finds the file type. It could be smarter about the name.
                        file_name = f"file_{file_count}{match_dict[language_match]}"
                        file_path = export_path + "/" + file_name
                # write the "files that represent lines here by writing each individual line"
                with open(file_path, "w") as file:
                    for line in lines[1:-1]:
                        file.write(line)
                file_count += 1


def populate_tree_view(history_sort_choice) -> Dict:

    previous_chats = {}

    if history_sort_choice == "date":
        dates = Chat.select()
        for tdate in dates:
            #this_date = datetime.strptime(tdate.created_at, "%Y-%m-%d").date()
            #logging.info(this_date.created_at)
            this_date = datetime.date(tdate.created_at)
            chats_on_date = Chat.select().where(fn.date_trunc("day", Chat.created_at) == this_date)
            previous_chats[str(this_date)] = chats_on_date
    elif history_sort_choice == "contexts":
        contexts = Context.select()
        for context in contexts:
            chats_under_context = Chat.select().where(Chat.context_id == context.id)
            previous_chats[str(context.text)] = chats_under_context
    else:
        topics = Topic.select()
        for topic in topics:
            if topic.text != "default":
                chat_under_topic = Chat.select().where(Chat.topic_id == topic.id)
                previous_chats[str(topic.text)] = chat_under_topic
    return previous_chats


async def chat_with_llm_UI(url: str, 
    question: str, MESSAGES: List, model_name: str, model_id: str, context_id: str, topic_id: str, file: str
) -> List:

    if file:
        file_input = open_file(file)
        question = f"{question}. Here is my file: {file_input}"
        file = False

    user_input = generate_input_dict(question)

    MESSAGES.append(user_input)

    api_endpoint = generate_endpoint(url, "chat")
    data = generate_data_for_chat(MESSAGES, model_name)

    response = await post_to_llm(api_endpoint, data)
    response_json = response.json()

    answer_key, answer = parse_answers(response_json)

    # append answer to messages
    MESSAGES.append(response_json[answer_key])

    logging.debug("Answer: {0}".format(answer))

    # save messages
    chat_id = Chat.create(
        question=question,
        answer=answer,
        context_id=context_id,
        topic_id=topic_id,
        llm_model_id=model_id,
    )

    logging.debug("record saved as {0}".format(chat_id))
    return chat_id, answer, MESSAGES


async def create_and_apply_chat_topic_ui(url: str, 
    chat_object_list: List, MESSAGES: List, model_name: str
) -> None:
    # setup vars
    api_endpoint = generate_endpoint(url, "chat")
    data = generate_data_for_chat(MESSAGES, model_name)
    response = await post_to_llm(api_endpoint, data)
    logging.debug(response.json())
    _, topic_summary = parse_answers(response.json())

    # compare summary to existing topics
    topic_id = compare_topics(topic_summary)
    if topic_id is None:
        topic_id = Topic.create(text=topic_summary)

    # update topic_id for chats
    for current_chat in chat_object_list:
        current_chat.update_chat_topic_from_summary(topic_id)

def resume_previous_chats_ui(selected_chats: List) -> List:
    topic_id_list = []
    context_id_list = []
    MESSAGES = []
    context_id = 1
    topic_id = 1
    for chat in selected_chats:
        topic_id_list.append(chat.topic_id)
        context_id_list.append(chat.context_id)
        MESSAGES.append(generate_input_dict(chat.question))
        MESSAGES.append({"role": "assistant", "content": chat.answer})

    if len(context_id_list) > 0:
        context_id = statistics.mode(context_id_list)
        topic_id = statistics.mode(topic_id_list)

        context_obj = Context.get_by_id(context_id)
        context_dict = create_context_dict(context_obj.text)

        MESSAGES = [context_dict] + MESSAGES
    return MESSAGES, topic_id

def export_chat_as_file_ui(export_path: str, chats: List, code_only: bool) -> None:
    """export chats passed into to export"""
    logging.debug("code only: {0}".format(code_only))
    # set file types
    file_type = "text"
    if code_only == True:
        file_type = "code"

    # ensure path
    if export_path is None:
        export_path = input(
            "Enter the /path/file to export your chats as text. Use folder only for code: "
        )
    export_path = parse_export_path(export_path, code_only)

    logging.info(export_path)
    
    # try to write files to path
    try:

        match file_type:
            case "text":
                logging.info("Exporting Text file")
                export_text_file(export_path, chats)
            case "code":
                logging.info("chat len {}".format(len(chats)))
                logging.info("Exporting text_and_code file")
                export_code_file(export_path, chats)

    except PermissionError:
        logging.info(f"Error: Permission denied for {export_path}'.")
    except FileNotFoundError:
         logging.info(f"Error: The path '{export_path}' cannot be created.")
    except Exception as e:
         logging.info(f"Unexpected error: {e}")
