import logging

from textual import on
from textual.reactive import reactive, var
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button,
    DirectoryTree,
    Input,
    Label,
    RadioSet,
    RadioButton,
    Static,
)

from src.myllamacli.chats import parse_export_path
from src.myllamacli.ui_modal_and_widgets import FileSelected

class FilePathScreen(Screen):
    CSS = """
    .visible {
        opacity: 100;
    }
    

    .hidden {
        opacity: 0;
    }
    """

    def __init__(self, input_class: str, chat_object_list: list, is_directory: bool)  -> None:
        super().__init__()
        self.input_class = input_class
        self.isdir = is_directory
        self.chat_object_list = chat_object_list


    def compose(self) -> ComposeResult:
        if self.input_class == "hidden":
            dtlbl = "Select File"
        else:
            dtlbl = "Select Directory"

        yield Static("\n")
        yield Static("Click to Close Settings Window without a Path")
        yield Button("Close Settings", id="CloseTree", variant="primary")
        yield Static("\n")
        yield Label(dtlbl, id="dtreelabel")
        yield DirectoryTree(path=parse_export_path("~", True), id="dirtree")
        yield Input(
            placeholder="Enter file name",
            id="FilePathInput",
            classes=self.input_class
        )
        with RadioSet(id="exportradio", classes=self.input_class):
            yield RadioButton("Export Entire Chat")
            yield RadioButton("Export Code Only")
        yield Button("Submit Path", id="submitpath", variant="primary", classes=self.input_class)


    @on(Button.Pressed, "#CloseTree")
    def close_file_screen(self, event: Button.Pressed) -> None:
        """ Handle buttons in close button in file screen."""
        logging.debug("CloseTree")
        self.dismiss()
    
    
    @on(Button.Pressed, "#submitpath")
    def submit_path_screen(self, event: Button.Pressed) -> None:
        """ Handle buttons in filepath screen."""
        # Adds directory selected below to input name and submit
        if self.isdir:
            # get file name from input and generate path
            input = self.query_one("#FilePathInput")
            file_name = input.value
            export_path = str(self.directory_path) + "/" + file_name
            logging.debug(f"export: {export_path}")

            # get choice of entire chat or code
            export_choice = self.query_one("#exportradio").pressed_index
            logging.debug(f"export_toggle: {export_choice}")
            if export_choice == 1:
                code_only = True
                self.notify("Exporting Chat. Please wait.")
            else:
                code_only = False
                self.notify("Exporting Code examples from Chat. Please wait.")

            if len(self.chat_object_list) > 0:
                export_chat_as_file_ui(export_path, self.chat_object_list, code_only)
                self.notify("Chats Exported")
            else: 
                self.notify("No Chats to export, chat a bit then try again.")
            self.dismiss()

    @on(DirectoryTree.FileSelected)
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        """ Handles tree when importing a file"""
        if not self.isdir:
            logging.debug(f"file: {event.path}")
            self.post_message(FileSelected(str(event.path)))
            self.dismiss()

    @on(DirectoryTree.DirectorySelected)
    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected):
        """ Handles tree when choosing Dir for saving"""
        if self.isdir:  
            logging.debug(f"directory: {event.path}")
            self.directory_path = event.path