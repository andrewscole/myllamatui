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
    Static,
    Tree,
)

# from typing import Any, Touple, List

from myllamacli.db_models import Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings
from myllamacli.shared_utils import set_database_path
from myllamacli.setup_utils import setup_db_and_initialize_defaults
from myllamacli.chats import (
    chat_with_llm_UI,
    create_and_apply_chat_topic_ui,
    resume_previous_chats_ui,
    save_chat,
)
from myllamacli.topics_contexts_categories import generate_current_topic_summary

from myllamacli.ui_shared import model_choice_setup, context_choice_setup
from myllamacli.ui_widgets_messages import QuestionAsk, FileSelected, SettingsChanged
from myllamacli.ui_file_screen import FilePathScreen
from myllamacli.ui_settings_screen import SettingsScreen
from myllamacli.ui_modal_screens import QuitScreen

# CONSTANT PROMPTS
from myllamacli.prompts import (
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

    TITLE = "LlamaTerminal"
    SUB_TITLE = "Local UI for for accessing Ollama"

    def __init__(self):
        """Custom init for app"""
        super().__init__()
        # main window
        self.url = ""
        self.chat_sort_choice = "topics"
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
        self.directory_path = False

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
            yield VerticalScroll(id="CurrentChant_MainChatWindow")
            #yield Select(
            #    iter((sort_choice, sort_choice) for sort_choice in ["Topics", "Dates"]),
            #    prompt="Sort Chats By:",
            #    id="ChatHistorySelect_topright",
            #)
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
    ) -> None:
        """Create and mount widgets for chat"""
        chatcontainer = self.query_one("#CurrentChant_MainChatWindow")

        # mount date and model info
        if previouschatdate is not None:
            qdate = previouschatdate
        else:
            qdate = "Today"

        model_date_display_info = f"{str(model_name)} - {qdate}"

        # mount to chat container
        if question != EVALUATION_QUESTION:
            question_container = Markdown(question, classes="cssquestion")

        else:
            question_container = Markdown("Evaluation:", classes="cssquestion")


        if model_date_display_info != self.model_date_display_info:
            self.model_date_display_info = f"{str(model_name)} - {qdate}"

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
        """ create a dict of {topic object : [list of chats under topic]}"""
        previous_chats = {}
        topics = Topic.select()
        for topic in topics:
            if topic.text != "default":
                chat_under_topic = Chat.select().where(Chat.topic_id == topic.id)
                previous_chats[topic] = chat_under_topic
        return previous_chats

    def update_tree(self):
        """Update tree with selections from the DB"""

        tree = self.query_one(Tree)
        logging.info("sort choice: {}".format(self.chat_sort_choice))
        tree = self.query_one(Tree)
        tree.clear()
        previous_chats = tree.root.expand()
        
        categories = Category.select()
        tree_dict = {}

        ##### keep this works
        # setup categories (level 1) 
        for category_name in categories:
            if str(category_name.text) != "default":
                tree_dict[str(category_name.id)] = previous_chats.add(str(category_name.text), allow_expand=True)
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

        answer, self.LLM_MESSAGES = await chat_with_llm_UI(
            url,
            question,
            context,
            messages,
            model_name,
            file_path,
        )

        if ACURATE_RESPONSE not in answer:
            # record
            chat_object_id = save_chat(
                question, answer, self.context_choice_id, self.topic_id, model_id
            )

            # add to list for topic updates later
            self.chat_object_list.append(chat_object_id)

            # display
            self.add_wdg_to_scroll(question, answer, model_name, None)

    #################################
    ##### ACTIONS | Main Window #####
    #################################
    @on(Select.Changed, "#ContextDisplay_topbar")
    def context_select_changed(self, event: Select.Changed) -> None:
        """Get Selection from Context select box."""
        logging.info("context_choice:{}".format(event))
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
            self.notify("Please Note: This will make the 'Thinking' phase take at least twice as long!", severity="warning")


    @on(Select.Changed, "#ChatHistorySelect_topright")
    def sort_choice_select_changed(self, event: Select.Changed) -> None:
        """Get Selection from Chat History select box."""

        logging.debug("chathistort_choice: {}".format(event.value))
        self.chat_sort_choice = str(event.value).lower()

        # move to on_mount
        self.update_tree()

    # submit button
    @on(Input.Submitted, "#question_text")
    @on(Button.Pressed, "#SubmitQuestion")
    async def on_input_changed(self, event: Button.Pressed) -> None:
        """Manage Submit Question Button and input."""

        logging.debug("Question asked")

        # setup question
        input = self.query_one("#question_text")
        question = input.value

        # setup loading graphic
        self.query_one("#SubmitQuestion").loading = True
        input.loading = True
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

        # clean up file path as the data will already be in messages
        self.file_path = ""
        model_list = [llm_model.model for llm_model in LLM_MODEL.select()]
        if self.chats_loaded == False and str(self.followup_model_choice_name) in model_list:
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


    def view_previous_chats(self, label_name: str, choice_num: int) -> None:
        """ loads previous chats """

        # setup previous_chats list

        if label_name == "Current Chats":
            previous_chats = []
            for id in self.current_session_chat_object_list:
                chat_obj = Chat.get_by_id(id)
                previous_chats.append(chat_obj)
                self.chats_loaded = False
        else:
            previous_chats = Chat.select().where(Chat.topic_id == choice_num)
            self.chats_loaded = True


        # not take care of the visuals
        chatcontainer = self.query_one("#CurrentChant_MainChatWindow")


        for item in chatcontainer.children:
            item.remove()
        previous_chat_date = ""
        for chat in previous_chats:
            question = chat.question
            answer = chat.answer
            chatdate = str(chat.created_at).split()
            previous_chat_date = chatdate[0]

            # get model id
            llm_model = LLM_MODEL.get_by_id(chat.llm_model_id)

            self.add_wdg_to_scroll(
                question, answer, llm_model.model, previous_chat_date
            )

        reformatted_previous_chats, self.topic_id = resume_previous_chats_ui(
            previous_chats
        )

        # finally update on going session lists
        self.LLM_MESSAGES = self.LLM_MESSAGES + reformatted_previous_chats
        self.chat_object_list = list(previous_chats)


    async def on_tree_node_selected(self, event: Tree) -> None:
        """Load Old Chats in tree. If new just, save existing and clear."""
        await self.action_save()
        top_layer_offset = len(Category.select())
        logging.info(f"categories len: {top_layer_offset}")
        choice_num = event.node.id - top_layer_offset
        if choice_num < 1:
            choice_num = 0

        logging.info(
            "Tree label, id, and choice selected: {0}, {1}, {2}".format(event.node.label, event.node.id, choice_num)
        )
        if event.node.label == "New Chat":
            # reset to default topic id
            self.topic_id = 1
        else:
            self.view_previous_chats(event.node.label, choice_num)
   

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
            self.push_screen(FilePathScreen("hidden", self.chat_object_list, False))

        elif event.button.id == "export":
            logging.debug("export")
            self.push_screen(FilePathScreen("visible", self.chat_object_list, True))

    def on_file_selected(self, message: FileSelected) -> None:
        self.file_path = message.path
        logging.info(self.file_path)

    def on_settings_changed(self, message: SettingsChanged) -> None:
        logging.info(message.url_changed)
        # messages have to be strings!
        if message.context_changed != "":
            logging.info("context")
            # self.query_one("#ContextDisplay_topbar").set_options(model_choice_setup())
            self.query_one("#ContextDisplay_topbar").set_options(context_choice_setup())

        if message.topic_changed != "" or message.category_changed != "":
            logging.info("topic")
            self.query_one("#ChatHistoryDisplay_sidebar").clear

        if message.model_changed != "":
            self.query_one("#ModelDisplay_topbar").set_options(model_choice_setup())
            self.query_one("#VerificationModelSelect_topbar").set_options(
                model_choice_setup()
            )

        if message.url_changed != "":
            self.url = message.url_changed
        
        self.update_tree()


    def done_loading(self) -> None:
        self.query_one("#SubmitQuestion").loading = False
        self.query_one("#question_text").loading = False

    async def add_topic_to_chat(self) -> None:
        """Save a summary of the chats and quit."""
        self.notify(
            "Updating Chat Topics. This will take a few seconds.",
            severity="information",
        )
        logging.debug(len(self.chat_object_list))
        await create_and_apply_chat_topic_ui(
            self.url,
            self.chat_object_list,
            self.LLM_MESSAGES,
            self.model_choice_name,
        )

    async def action_save(self) -> None:
        """Save a summary of the chats and quit."""
        if len(self.chat_object_list) > 0 and self.topic_id == 1:
            logging.debug("saving chats")
            self.push_screen(
                QuitScreen("Updating Chat Topics. This will take a few seconds.")
            )
            await self.add_topic_to_chat()
            self.pop_screen()
            self.current_session_chat_object_list = self.current_session_chat_object_list + self.chat_object_list
            self.chat_object_list = []

    async def action_quit(self) -> None:
        """Save a summary of the chats and quit."""
        if len(self.chat_object_list) > 0 and self.topic_id == 1:
            self.push_screen(
                QuitScreen("Updating Chat Topics. The app will exit in a few seconds.")
            )
            logging.debug(len(self.chat_object_list))
            await self.add_topic_to_chat()
        self.app.exit()


    async def on_load(self) -> None:
        """ First time Database and inits setup here """
        if not os.path.exists(set_database_path()):
            await setup_db_and_initialize_defaults()

    def on_mount(self) -> None:
        """ start up paramaters here"""

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
