import logging

from peewee import *
from textual import on  # , work
from textual.app import App, ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Markdown,
    Select,
    Static,
    TextArea,
    Tree,
)

# from typing import Any, Touple, List

from myllamacli.db_models import Context, Topic, LLM_MODEL, Chat, CLI_Settings
from myllamacli.chats import (
    populate_tree_view,
    chat_with_llm_UI,
    create_and_apply_chat_topic_ui,
    resume_previous_chats_ui
)
from src.myllamacli.topics_contexts import generate_current_topic_summary, create_context_dict

from src.myllamacli.ui_shared import model_choice_setup, context_choice_setup
from myllamacli.ui_modal_widget import QuitScreen, QuestionAsk, FileSelected, SettingsChanged
from src.myllamacli.ui_file_screen import FilePathScreen
from src.myllamacli.ui_settings_screen import SettingsScreen


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
        """ Custom init for app"""
        super().__init__()
        # main window
        ##### at start pull in the settings from the DB ####
        self.url = self.load_get_current_settings().url
        self.chat_sort_choice = "topics"
        self.model_choice_id = self.load_current_model().id
        self.model_choice_name = self.load_current_model().model
        self.context_choice_id = self.load_current_context().id
        self.context_choice_text = self.load_current_context().text
        self.topic_id = 1
        self.chats_loaded = False

        # Files
        self.file_path = False
        self.directory_path = False

        # chats
        self.LLM_MESSAGES = []
        self.previous_messages = []
        self.chat_object_list = []

        # settings window
        self.settings_edit_selector = ""
        self.context_switcher_file_or_export = ""
        self.model_to_delete = ""

    ###### setup inits by calling database ########
    def load_get_current_settings(self):
        return CLI_Settings.get_by_id(1)
    
    def load_current_model(self):
        return LLM_MODEL.get_by_id(self.load_get_current_settings().llm_model_id)

    def load_current_context(self):
        return Context.get_by_id(self.load_get_current_settings().context_id)

    ######## GUI ##########
    def compose(self) -> ComposeResult:
        """ setup GUI for Application. """


        # setup tree. THE FU



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
                model_choice_setup(), prompt="Choose Model:", id="ModelDisplay_topbar"
            )
            yield Select(
                iter(
                    (sort_choice, sort_choice) for sort_choice in ["Topics", "Dates"]
                ),
                prompt="Sort Chats By:",
                id="ChatHistorySelect_topright",
            )
            yield VerticalScroll(id="CurrentChant_MainChatWindow")
            yield Tree("Previous Chats", id="ChatHistoryDisplay_sidebar")
            yield QuestionAsk(id="QuestionAsk_bottombar")
            yield Button("Add File", id="filepathbutton", variant="primary")
            yield Button("Export Chats", id="export", variant="default")
        yield Footer()

    #############################
    #### Widget Helper Defs ####
    #############################

    def add_wdg_to_scroll(
        self, chatcontainer, question, answer, chatdate, previouschatdate
    ):
        """Create and mount widgets for chat"""
        qwidget = Markdown(question, classes="cssquestion")
        amarkdown = Markdown(answer, classes="cssanswer")
        # I think the trick here is going to be to split the text and have markdown for the text and then
        # use text area for the code. I probably want to create a virtical that governs this and call it here.
        #amarkdown = TextArea(answer, classes="cssanswer", language="markdown")

        if chatdate is not None and chatdate != previouschatdate:
            qdate = Static(chatdate, classes="cssdate")
            chatcontainer.mount(qdate)
        # mount this last either way
        chatcontainer.mount(qwidget)
        chatcontainer.mount(amarkdown)

    def action_remove_chat(self) -> None:
        """Clear chats."""
        mounted_labels = self.query_one("#question_label")
        mounted_markdowns = self.query_one("#answer_markdown")
        mounted_labels.remove()
        mounted_markdowns.remove()


    def update_tree(self, tree):
        """Update tree with selections from the DB"""
        logging.debug("sort choice: {}".format(self.chat_sort_choice))
        tree.clear()
        old_chats = tree.root.expand()
        old_chat_list = populate_tree_view(self.chat_sort_choice)
        for old_chat in old_chat_list:
            old_chats.add_leaf(old_chat)
        old_chats.add_leaf("New Chat")
        return tree


    #################################
    ##### ACTIONS | Main Window #####
    #################################
    async def on_tree_node_selected(self, event: Tree) -> None:
        """Load Old Chats in tree. If new just, save existing and clear."""
        #if len(self.chat_object_list) > 0:
        #    await self.action_save()
        #    self.chat_object_list = []
        await self.action_save()
        choice_num = event.node.id + 1
        logging.debug("Tree label and id selected: {0}, {1}".format(event.node.label, choice_num))

        if event.node.label == "New Chat":
            # reset to default topic id
            self.topic_id = 1
        else:
            if self.chat_sort_choice == "topics":
                previous_chats = Chat.select().where(Chat.topic_id == choice_num)
            else:
                # self.chat_sort_choice == "dates":
                ##### switch this to dates #####
                previous_chats = Chat.select().where(Chat.context_id == choice_num)

            chatcontainer = self.query_one("#CurrentChant_MainChatWindow")

            for item in chatcontainer.children:
                item.remove()
            previous_chat_date = ""
            for chat in previous_chats:
                question = chat.question
                answer = chat.answer
                chatdate = str(chat.created_at).split()
                self.add_wdg_to_scroll(
                    chatcontainer, question, answer, chatdate[0], previous_chat_date
                )
                previous_chat_date = chatdate[0]
            reformatted_previous_chats, self.topic_id = resume_previous_chats_ui(previous_chats)
            self.LLM_MESSAGES = self.LLM_MESSAGES + reformatted_previous_chats
            self.chat_object_list = list(previous_chats)
            self.chats_loaded = True

    @on(Select.Changed, "#ContextDisplay_topbar")
    def context_select_changed(self, event: Select.Changed) -> None:
        """ Get Selection from Context select box. """
        logging.debug("context_choice:{}".format(event))
        self.context_choice_id = str(event.value)
        context_obj = Context.get_by_id(str(event.value))
        context_text = context_obj.text

        # create context dict and add to messages when change occurs
        context_dict = create_context_dict(context_text)
        self.LLM_MESSAGES.append(context_dict)

    @on(Select.Changed, "#ModelDisplay_topbar")
    def select_model_changed(self, event: Select.Changed) -> None:
        """ Get Selection from Model select box. """
        self.model_choice_id = str(event.value)
        logging.debug("Model: {}".format(self.model_choice_id))
        model_obj = LLM_MODEL.get_by_id(self.model_choice_id)
        self.model_choice_name = model_obj.model
        logging.debug("Model name: {}".format(self.model_choice_name))

    @on(Select.Changed, "#ChatHistorySelect_topright")
    def sort_choice_select_changed(self, event: Select.Changed) -> None:
        """ Get Selection from Chat History select box. """

        logging.debug("chathistort_choice: {}".format(event.value))
        self.chat_sort_choice = str(event.value).lower()
        tree = self.query_one(Tree)
        self.update_tree(tree)

    # submit button
    @on(Input.Submitted, "#question_text")
    @on(Button.Pressed, "#SubmitQuestion")
    async def on_input_changed(self, event: Button.Pressed) -> None:
        """ Manage Submit Question Button and input. """

        logging.debug("Question asked")
        chatcontainer = self.query_one("#CurrentChant_MainChatWindow")

        input = self.query_one("#question_text")
        question = input.value

        self.query_one("#SubmitQuestion").loading = True
        input.loading = True

        # call LLM 
        logging.debug("questions: {}".format(question))
        logging.info(self.url)        
        chat_object_id, answer, self.LLM_MESSAGES = await chat_with_llm_UI(
            self.url,
            question,
            self.LLM_MESSAGES,
            self.model_choice_name,
            self.model_choice_id,
            self.context_choice_id,
            self.topic_id,
            self.file_path,
        )

        self.chat_object_list.append(chat_object_id)
        self.done_loading()
        self.add_wdg_to_scroll(chatcontainer, question, answer, None, None)

        #clear input to ensure questions is only asked once
        input.clear()
        # reset file path so that the file isn't repeatedly reloaded
        self.file_path = False


    @on(Button.Pressed, "#settings")
    def add_settings_screen_to_stack(self, event: Button.Pressed) -> None:
        logging.debug("settings")
        self.push_screen(SettingsScreen(self.url))

    # Filepath and File export buttons
    @on(Button.Pressed, "#export")
    @on(Button.Pressed, "#filepathbutton")
    def addfile_button_changed(self, event: Button.Pressed) -> None:
        """ Handle File buttons in the Main Window """
        if event.button.id == "filepathbutton":
            logging.debug("filepathbutton")
            self.push_screen(FilePathScreen("hidden", self.chat_object_list, False))

        elif event.button.id == "export":
            logging.debug("export")
            self.push_screen(FilePathScreen("visible", self.chat_object_list, True))

    ##################################
    ### Get Data Back from Screens ###
    ##################################

    def on_file_selected(self, message: FileSelected) -> None:
        self.file_path = message.path
        logging.info(self.file_path)

    def on_settings_changed(self, message: SettingsChanged) -> None:
        logging.info(message.url_changed)
        # messages have to be strings!
        if message.context_changed != "":
            logging.info("context")
            #self.query_one("#ContextDisplay_topbar").set_options(model_choice_setup())
            self.query_one("#ContextDisplay_topbar").set_options(context_choice_setup())

        if message.topic_changed != "":
            logging.info("topic")
            self.query_one("#ChatHistoryDisplay_sidebar").clear

        if message.model_changed != "":
            self.query_one("#ModelDisplay_topbar").set_options(model_choice_setup())

        if message.url_changed != "":
            self.url = message.url_changed

    ##### close buttons for file, moving to filescressn class




    ####################################
    ##### ACTIONS | Settings Window ####
    ####################################

    ##### add a init section ####
    def done_loading(self) -> None:
        self.query_one("#SubmitQuestion").loading = False
        self.query_one("#question_text").loading = False

    async def add_topic_to_chat(self) -> None:
        """Save a summary of the chats and quit."""
        self.notify(
            "Updating Chat Topics. This will take a few seconds.", severity="information"
        )
        logging.debug(len(self.chat_object_list))
        summary_context = generate_current_topic_summary()
        self.LLM_MESSAGES.append(summary_context)
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
            self.push_screen(QuitScreen("Updating Chat Topics. This will take a few seconds."))
            await self.add_topic_to_chat()
            self.pop_screen()
            self.chat_object_list = []


    async def action_quit(self) -> None:
        """Save a summary of the chats and quit."""
        if len(self.chat_object_list) > 0 and self.topic_id == 1:
            self.push_screen(QuitScreen("Updating Chat Topics. The app will exit in a few seconds."))
            logging.debug(len(self.chat_object_list))
            await self.add_topic_to_chat()
        self.app.exit()


if __name__ == "__main__":
    app = OllamaTermApp()
    app.run()