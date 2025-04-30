import logging
import os
import re

from typing import List


# export related definitions
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

    logging.debug(
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

    logging.debug("length of chats: {0}".format(len(chats)))
    logging.debug(chats[0].id)
    for i in range(0, len(chats)):
        chat = chats[i]
        file_count = 1
        #single_chat = chat.answer
        logging.debug("chat {i}")
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
                        ### opted to export by relativechat
                        file_name = f"chat{i + 1}_file{file_count}{match_dict[language_match]}"
                        file_path = export_path + "/" + file_name
                # write the "files that represent lines here by writing each individual line"
                with open(file_path, "w") as file:
                    for line in lines[1:-1]:
                        file.write(line)
                file_count += 1


def export_chat_as_file_ui(export_path: str, chats: List, code_only: bool) -> None:
    """export chats passed into to export"""
    
    logging.debug("code only: {0}".format(code_only))
    # set file types
    file_type = "text"
    if code_only == True:
        file_type = "code"

    export_path = parse_export_path(export_path, code_only)

    logging.debug(export_path)
    
    # try to write files to path
    try:

        match file_type:
            case "text":
                logging.info("Exporting Text file")
                export_text_file(export_path, chats)
            case "code":
                logging.debug("chat len {}".format(len(chats)))
                logging.info("Exporting code files only")
                export_code_file(export_path, chats)

    except PermissionError:
        logging.warning(f"Error: Permission denied for {export_path}'.")
    except FileNotFoundError:
         logging.warning(f"Error: The path '{export_path}' cannot be created.")
    except Exception as e:
         logging.warning(f"Unexpected error: {e}")
