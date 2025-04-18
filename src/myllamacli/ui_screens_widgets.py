import logging

from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Input,
    Label,
    RadioSet,
    RadioButton,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from myllamacli.db_models import LLM_MODEL, Chat
from src.myllamacli.ui_shared import model_choice_setup, context_choice_setup, create_topics_select
from myllamacli.chats import parse_export_path

###### Screens #######

class SettingsScreen(Screen):
    updated_url = reactive("")

    # might not need this
    #def __init__(self):
    #    super().__init__()
    #    self.close_message = ""

    def compose(self) -> ComposeResult:

        yield Static("\n")
        yield Button("Close Settings Window", id="CloseSetting", variant="primary")
        yield Static("\n")

        yield Label("Choose settings to edit:")
        yield Static("\n")
        with TabbedContent():
            with TabPane("Edit URL", id="EditURL"):
                # set url
                yield Static("\n\n")
                
                yield Label(f"Current URL: {self.updated_url}", id="CurrentUrl")
                yield Button("UPDATE URL", id="UpdateUrl", variant="success")
                yield Input(
                    placeholder="current url", id="inputurl", classes="cssquestion_text"
                )
                yield Static("\n\nThe default for Ollama is:\nhttp://localhost:11434")

            with TabPane("Edit Contexts", id="EditContexts"):
                # new context
                yield Static("\n\n")
                yield Label("Add New Context")
                yield Input(
                    placeholder="Add New Context Here",
                    id="NewContextInput",
                    classes="cssquestion_text",
                )
                yield Button("Add New Context", id="NewContext", variant="success")
                yield Static("\n")
                yield Label("Edit Existing Context")
                yield Select(
                    context_choice_setup(),
                    prompt="Choose Context:",
                    id="ContextEditChoose",
                )
                yield Input(
                    placeholder="Update Context Here",
                    id="EditContextInput",
                    classes="cssquestion_text",
                )
                yield Button("Update Context", id="EditContext", variant="success")

            with TabPane("Edit Topics", id="EditTopics"):

                # new topic
                yield Static("\n\n")
                yield Label("Add New Topic")
                yield Input(
                    placeholder="Add New Topic Here",
                    id="NewTopicInput",
                    classes="cssquestion_text",
                )
                yield Button("Add New Topic", id="NewTopic", variant="success")

                yield Static("\n")
                yield Label("Edit Existing Topic:")
                yield Select(
                    create_topics_select(), prompt="Choose Topic:", id="TopicEditChoose"
                )
                yield Input(
                    placeholder="Update Topic Here",
                    id="EditTopicInput",
                    classes="cssquestion_text",
                )
                yield Button("Save Topic Update", id="EditTopic", variant="success")

            with TabPane("Edit Models", id="EditModels"):
                yield Static("\n\n")
                yield Label("Pull New Models:")
                yield Button("Pull Model", id="PullModel", variant="success")
                yield Input(
                    placeholder="Enter Model to Pull Here",
                    id="ModelInput",
                    classes="cssquestion_text",
                )
                yield Static("\n")

                yield Label("Current and Previously Used Models: ")
                yield self.models_datatable()
                yield Static("Select a model above and Click 'Delete Model' Button to remove the model")
                yield Static("\n")
                yield Label(f"To Delete: No Selection", id="model_to_delete_label")
                yield Button("Delete Model", id="DeleteModel", variant="warning")

    def models_datatable(self):
        all_models = LLM_MODEL.select()
        table = DataTable(id="models_data_table")
        table.add_columns(
            "name", "currently_available", "size", "downloaded", "Chats Used"
        )
        rows = []
        for model in all_models:
            logging.debug(model.id)
            model_usage = Chat.select().where(Chat.llm_model_id == model.id).count()
            download_date = str(model.modified_at).split(" ")[0]
            logging.debug(download_date)
            rows.append(
                (
                    str(model.model),
                    str(model.currently_available),
                    str(model.size),
                    str(download_date),
                    int(model_usage),
                )
            )
        table.add_rows(rows)
        table.zebra_stripes = True
        table.fixed_columns = 1
        return table

    @on(Button.Pressed, "#CloseSetting")
    def close_settings_screen(self, event: Button.Pressed) -> None:
        logging.debug("CloseSetting")            
        #self.dismiss(self.close_message)
        self.dismiss()


class FilePathScreen(Screen):
    CSS = """
    .visible {
        opacity: 100;
    }
    

    .hidden {
        opacity: 0;
    }
    """
    def __init__(self, input_class):
        super().__init__()
        self.input_class = input_class


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

###### Widgets in Main App #######          

class QuitScreen(ModalScreen):
    """Shows warning that I am qutting"""

    CSS = """
    QuitScreen {
        align: center middle;
    }
    """
    def __init__(self, qs_message):
        super().__init__()
        self.qs_message = qs_message

    def compose(self) -> ComposeResult:
        yield Label(self.qs_message, id="qa_savingmessage", classes="QuitScreen")
        

class QuestionAsk(HorizontalGroup):
    """Horizontal widiget group for asking questions."""

    CSS = """
    .cssquestion_text {
        row-span: 1;
        column-span: 6;
        color:rgb(253, 254, 255);
        background: transparent;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for button bar."""
        # these go on the bottom of the main screen
        yield Button("Submit", id="SubmitQuestion", variant="success")
        yield Input(
            placeholder="Type your question here",
            id="question_text",
            classes="cssquestion_text",
        )
