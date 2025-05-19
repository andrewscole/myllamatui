import logging
import os

from datetime import datetime
from typing import List, Dict, Tuple


from peewee import *

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Grid, VerticalScroll, Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Select,
    Tree,
)

from src.myllamacli.db_models import Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings
from src.myllamacli.init_files import set_database_path
from src.myllamacli.setup_utils import create_db, initialize_db_defaults
from src.myllamacli.chats import (
    chat_with_llm_UI,
    create_and_apply_chat_topic_ui,
    resume_previous_chats_ui,
    save_chat,
)
from src.myllamacli.import_export_files import (
    open_files_and_add_to_question,
    check_file_type,
)
from src.myllamacli.ui_shared import model_choice_setup, context_choice_setup
from src.myllamacli.ui_widgets_messages import (
    QuestionAsk,
    FileSelected,
    SettingsChanged,
    SupportNotifyRequest,
)
from src.myllamacli.ui_file_screen import FilePathScreen
from src.myllamacli.ui_settings_screen import SettingsScreen
from src.myllamacli.ui_modal_screens import QuitScreen

# CONSTANT PROMPTS
from src.myllamacli.prompts import (
    DO_NOT_MAKEUP,
    EVALUATION_QUESTION,
    EVALUTATE_CONTEXT,
    ACURATE_RESPONSE,
)

logging.basicConfig(
    filename="myllama.log",
    level=logging.INFO,
    filemode="a",  # 'w' to overwrite, 'a' to append
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class OllamaTermApp(App):
    """A Textual app to manage ollama chats and models."""

    CSS_PATH = "css_grid_setup.tcss"

    BINDINGS = [
        ("s", "save", "Update Chat Topic"),
        ("q", "quit", "Quit"),
    ]

    TITLE = "LlamaTerminalUI"
    SUB_TITLE = "Local UI for for accessing Ollama"

    def __init__(self) -> None:
        """Custom init for app"""
        super().__init__()
        # main window
        self.url = ""
        self.model_choice_id = ""
        self.model_choice_name = ""
        self.context_choice_id = ""
        self.context_choice_text = ""
        self.followup_model_choice_id = ""
        self.followup_model_choice_name = ""
        self.topic_id = 1
        self.chats_loaded = False

        # Files
        self.file_path = ""

        # chats
        self.LLM_MESSAGES = []
        self.previous_messages = []
        self.chat_object_list = []
        self.current_session_chat_object_list = []

        # display
        self.model_date_display_info = ""

        # settings window
        self.settings_edit_selector = ""
        self.context_switcher_file_or_export = ""
        self.model_to_delete = ""

    ######## GUI ##########
    def compose(self) -> ComposeResult:
        """setup GUI for Application."""

        yield Header("Ollama Chats Terminal App")

        with Grid():
            yield Button(
                "Settings",
                id="settings",
                variant="primary",
                classes="SettingsButton_topright",
            )
            yield Select(
                context_choice_setup(),
                prompt="Choose Context:",
                id="ContextDisplay_topbar",
            )
            yield Select(
                model_choice_setup(),
                prompt="Choose Primary Model:",
                id="ModelDisplay_topbar",
            )
            yield Select(
                model_choice_setup(),
                prompt="Verificatin Model:",
                id="VerificationModelSelect_topbar",
            )
            yield VerticalScroll(id="CurrentChat_MainChatWindow")
            yield Tree("Previous Chats", id="ChatHistoryDisplay_sidebar")
            yield QuestionAsk(id="QuestionAsk_bottombar")
            yield Button("Add File", id="filepathbutton", variant="primary")
            yield Button("Export Chats", id="export", variant="default")
        yield Footer()

    #############################
    #### Widget Helper Defs ####
    #############################

    def add_wdg_to_scroll(
        self,
        question: str,
        answer: str,
        model_name: str,
        previouschatdate: str,
        chat_id: str,
        chatcontainer,
    ) -> None:
        """Create and mount widgets for chat"""

        # mount date and model info
        if previouschatdate is not None:
            qdate = previouschatdate
        else:
            qdate = "Today"

        model_date_display_info = f"{str(model_name)} - {qdate} - chat id: {chat_id}"

        # mount to chat container
        if question != EVALUATION_QUESTION:
            question_container = Markdown(question, classes="cssquestion")

        else:
            question_container = Markdown("Evaluation:", classes="cssquestion")

        if model_date_display_info != self.model_date_display_info:
            self.model_date_display_info = (
                f"{str(model_name)} - {qdate} - chat id: {chat_id}"
            )

        chatcontainer.mount(Label(self.model_date_display_info, classes="cssdate"))
        chatcontainer.mount(question_container)

        #### mount answer ####
        answer_container = Markdown(answer, classes="cssanswer")
        chatcontainer.mount(answer_container)

    def action_remove_chat(self) -> None:
        """Clear chats."""
        mounted_labels = self.query_one("#question_label")
        mounted_markdowns = self.query_one("#answer_markdown")
        mounted_labels.remove()
        mounted_markdowns.remove()

    def populate_tree_topic(self) -> Dict:
        """create a dict of {topic object : [list of chats under topic]}"""
        previous_chats = {}
        topics = Topic.select()
        for topic in topics:
            if topic.text != "default":
                chat_under_topic = Chat.select().where(Chat.topic_id == topic.id)
                previous_chats[topic] = chat_under_topic
        return previous_chats

    def update_tree(self) -> None:
        """Update tree with selections from the DB"""

        tree = self.query_one(Tree)
        tree = self.query_one(Tree)
        tree.clear()
        previous_chats = tree.root.expand()

        categories = Category.select()
        tree_dict = {}

        ##### keep this works
        # setup categories (level 1)
        for category_name in categories:
            if str(category_name.text) != "default":
                tree_dict[str(category_name.id)] = previous_chats.add(
                    str(category_name.text), allow_expand=True
                )
        tree.root.add("Current Chat")
        tree.root.add("New Chat")

        # topic_list is a list of Topic objects
        topic_list = self.populate_tree_topic()
        for single_topic in topic_list:
            tree_dict[str(single_topic.category_id)].add(str(single_topic.text))

    ### this is the main wrapper for the chat ####
    async def chat_record_display(
        self,
        url: str,
        question: str,
        context: str,
        messages: list,
        model_name: str,
        model_id: str,
        file_path: str,
    ) -> None:
        """Wraps chat call, saving to db, and displaying"""
        # chat

        # send submitted quesiton to llm
        submitted_question = question

        if file_path != "":
            self.notify(
                "Adding Files to Question. This might take a second",
                severity="information",
            )
            submitted_question = open_files_and_add_to_question(
                question, self.file_path
            )
            question = question + f"{self.file_path}"

        logging.debug(submitted_question)

        answer, self.LLM_MESSAGES = await chat_with_llm_UI(
            url,
            submitted_question,
            context,
            messages,
            model_name,
        )

        if ACURATE_RESPONSE not in answer:
            # record
            # send question to db - with path only if needed
            chat_object_id = save_chat(
                question, answer, self.context_choice_id, self.topic_id, model_id
            )

            # add to list for topic updates later
            self.chat_object_list.append(chat_object_id)
            self.current_session_chat_object_list.append(chat_object_id)

            # display
            chatcontainer = self.query_one("#CurrentChat_MainChatWindow")

            self.add_wdg_to_scroll(
                question, answer, model_name, None, str(chat_object_id.id), chatcontainer,

            )

    #################################
    ##### ACTIONS | Main Window #####
    #################################
    @on(Select.Changed, "#ContextDisplay_topbar")
    def context_select_changed(self, event: Select.Changed) -> None:
        """Get Selection from Context select box."""
        logging.debug("context_choice:{}".format(event))
        self.context_choice_id = str(event.value)
        context_obj = Context.get_by_id(str(event.value))
        context_text = context_obj.text
        self.context_choice_text = context_text

    @on(Select.Changed, "#ModelDisplay_topbar")
    def select_primary_model_changed(self, event: Select.Changed) -> None:
        """Get Selection from Model select box."""
        self.model_choice_id = str(event.value)
        logging.debug("Primary Model: {}".format(self.model_choice_id))
        model_obj = LLM_MODEL.get_by_id(self.model_choice_id)
        self.model_choice_name = model_obj.model
        logging.debug("Primary Model name: {}".format(self.model_choice_name))

    @on(Select.Changed, "#VerificationModelSelect_topbar")
    def select_verification_model_changed(self, event: Select.Changed) -> None:
        """Get Selection from Model select box."""
        self.followup_model_choice_id = str(event.value)
        logging.debug("Follow upModel: {}".format(self.followup_model_choice_id))
        model_obj = LLM_MODEL.get_by_id(self.followup_model_choice_id)
        self.followup_model_choice_name = model_obj.model
        logging.debug("Folloup Model name: {}".format(self.followup_model_choice_name))
        if int(event.value) > 0:
            self.notify(
                "Please Note: This will make the 'Thinking' phase take at least twice as long!",
                severity="warning",
            )

    # submit button
    @on(Input.Submitted, "#question_text")
    @on(Button.Pressed, "#SubmitQuestion")
    async def on_input_changed(self, event: Button.Pressed) -> None:
        """Manage Submit Question Button and input."""

        logging.debug("Question asked")

        # setup question
        input = self.query_one("#question_text")
        question = input.value
        
        # clean up file path as the data will already be in messages
        model_list = [llm_model.model for llm_model in LLM_MODEL.select()]

        # setup loading graphic
        self.query_one("#SubmitQuestion").loading = True
        input.loading = True

        logging.debug("saving chats")

        # so this causes a issue that I think is probably async render related, defaulting to loading first.

        #querying_note = f"Querying {self.model_choice_name}. This could take a while, particularly when using models over 10b. Time out is set to 15 min."
        #if str(self.followup_model_choice_name) in model_list:
        #    f"Querying {self.model_choice_name} and evaluating with {self.followup_model_choice_name} This will take a while. Time out is set to 15 min per call."
        #self.push_screen(
        #    QuitScreen(querying_note)
        #)

        # call LLM
        logging.debug("questions: {}".format(question))

        await self.chat_record_display(
            self.url,
            question,
            self.context_choice_text,
            self.LLM_MESSAGES,
            self.model_choice_name,
            self.model_choice_id,
            self.file_path,
        )

        # reset files to ensure that they isn't added repeatdly
        self.file_path = ""
        if (
            self.chats_loaded == False
            and str(self.followup_model_choice_name) in model_list
        ):
            # this should be a call with a return
            logging.info(
                f"{self.followup_model_choice_id} set as followup. Evaluating update."
            )
            # note I'm saving chat with original context
            await self.chat_record_display(
                self.url,
                EVALUATION_QUESTION,
                EVALUTATE_CONTEXT,
                self.LLM_MESSAGES,
                self.followup_model_choice_name,
                self.followup_model_choice_id,
                self.file_path,
            )

        # clean up after chat is complete
        self.done_loading()
        input.clear()
        self.chats_loaded = False

    def view_previous_chats(self, previous_chats: list) -> None:
        """loads previous chats"""

        chatcontainer = self.query_one("#CurrentChat_MainChatWindow")

        for item in chatcontainer.children:
            item.remove()
        previous_chat_date = ""
        for chat in previous_chats:
            chatdate = str(chat.created_at).split()
            previous_chat_date = chatdate[0]

            # get model id
            llm_model = LLM_MODEL.get_by_id(chat.llm_model_id)

            self.add_wdg_to_scroll(
                chat.question,
                chat.answer,
                llm_model.model,
                previous_chat_date,
                str(chat.id),
                chatcontainer,
            )

        reformatted_previous_chats, self.topic_id = resume_previous_chats_ui(
            previous_chats
        )

        # finally update on going session lists
        self.LLM_MESSAGES = self.LLM_MESSAGES + reformatted_previous_chats
        self.chat_object_list = list(previous_chats)

    async def on_tree_node_selected(self, event: Tree) -> None:
        """Load Old Chats in tree. If new just, save existing and clear."""

        logging.debug(f"Tree label, id, and choice selected: {event.node.label}")
        selected_subject = str(event.node.label)
        previous_chats = []
        if selected_subject == "New Chat":
            logging.debug("New Chat Selected")
            topic = Topic.get_by_id(1)
            save_list = Chat.select().where(Chat.topic_id == topic.id)
            for chat in save_list:
                logging.debug(f"new chat{chat} id {chat.topic_id}")
            self.topic_id = 1
            await self.action_save()
            # reset to default topic id
        elif selected_subject == "Current Chat":
            for id in self.current_session_chat_object_list:
                chat_obj = Chat.get_by_id(id)
                previous_chats.append(chat_obj)
                self.chats_loaded = False
        elif selected_subject in [topic.text for topic in Topic.select()]:
            topic = Topic.get(Topic.text == selected_subject)
            previous_chats = Chat.select().where(Chat.topic_id == topic.id)
            self.chats_loaded = True
        else:
            logging.debug("Category Selected")

        self.view_previous_chats(previous_chats)

    @on(Button.Pressed, "#settings")
    def add_settings_screen_to_stack(self, event: Button.Pressed) -> None:
        logging.debug("settings")
        self.push_screen(SettingsScreen(self.url))

    @on(Button.Pressed, "#iterations_mainscreen")
    def add_interations_screen_to_stack(self, event: Button.Pressed) -> None:
        logging.debug("settings")
        self.push_screen(
            IterationsScreen(self.iteration_count, self.model_info_as_string)
        )

    # Filepath and File export buttons
    @on(Button.Pressed, "#export")
    @on(Button.Pressed, "#filepathbutton")
    def addfile_button_changed(self, event: Button.Pressed) -> None:
        """Handle File buttons in the Main Window"""
        if event.button.id == "filepathbutton":
            logging.debug("filepathbutton")
            self.push_screen(FilePathScreen(True, self.chat_object_list))

        elif event.button.id == "export":
            logging.debug("export")
            self.push_screen(FilePathScreen(False, self.chat_object_list))

    def on_file_selected(self, message: FileSelected) -> None:
        self.file_path = message.path
        logging.debug(f"File Screen Path: {self.file_path}")

    def on_settings_changed(self, message: SettingsChanged) -> None:
        logging.info(message.url_changed)
        # messages have to be strings!
        if message.context_changed != "":
            # self.query_one("#ContextDisplay_topbar").set_options(model_choice_setup())
            self.query_one("#ContextDisplay_topbar").set_options(context_choice_setup())

        if message.topic_changed != "" or message.category_changed != "":
            self.query_one("#ChatHistoryDisplay_sidebar").clear

        if message.model_changed != "":
            self.query_one("#ModelDisplay_topbar").set_options(model_choice_setup())
            self.query_one("#VerificationModelSelect_topbar").set_options(
                model_choice_setup()
            )

        if message.url_changed != "":
            self.url = message.url_changed

        self.update_tree()

    # note this isn't currently in use. Leaving for now as it could be useful
    def on_notify_message(self, message: SupportNotifyRequest) -> None:
        logging.debug(f"SupportNotifyRequest: {message.content}, {message.severity}")
        self.notify(message.content, title=message.title)

    def done_loading(self) -> None:
        self.query_one("#SubmitQuestion").loading = False
        self.query_one("#question_text").loading = False

    async def add_topic_to_chat(self) -> None:
        """Save a summary of the chats and quit."""
        self.notify(
            "Updating Chat Topics. This will take a few seconds.",
            severity="information",
        )
        unparsed_chats = Chat.select().where(Chat.topic_id == 1)
        topic_id = await create_and_apply_chat_topic_ui(
            self.url,
            self.chat_object_list,
            self.LLM_MESSAGES,
            self.model_choice_name,
        )
        for current_chat in unparsed_chats:
            current_chat.update_chat_topic_from_summary(topic_id)

    async def action_save(self) -> None:
        """Save a summary of the chats and quit."""
        unparsed_chats = Chat.select().where(Chat.topic_id == 1)
        if len(unparsed_chats) > 0 and self.topic_id == 1:
            logging.debug("saving chats")
            self.push_screen(
                QuitScreen("Updating Chat Topics. This will take a few seconds.")
            )
            await self.add_topic_to_chat()
            self.pop_screen()
            self.chat_object_list = []

    async def action_quit(self) -> None:
        """Save a summary of the chats and quit."""

        await self.action_save()
        self.app.exit()

    async def on_load(self) -> None:
        """First time Database and inits setup here"""
        if not os.path.exists(set_database_path()):
            create_db()
            await initialize_db_defaults()


    def on_mount(self) -> None:
        """start up paramaters here"""

        current_settings = CLI_Settings.get_by_id(1)
        model = LLM_MODEL.get_by_id(current_settings.llm_model_id)
        context = Context.get_by_id(current_settings.context_id)

        self.url = current_settings.url
        self.model_choice_id = model.id
        self.model_choice_name = model.model
        self.context_choice_id = context.id
        self.context_choice_text = str(context.text) + DO_NOT_MAKEUP
        self.update_tree()


if __name__ == "__main__":
    app = OllamaTermApp()
    app.run()
