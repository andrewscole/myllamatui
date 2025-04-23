import logging
import re

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

from myllamacli.db_models import Context, Topic, LLM_MODEL, Chat, CLI_Settings
from myllamacli.chats import (
    chat_with_llm_UI,
    create_and_apply_chat_topic_ui,
    resume_previous_chats_ui,
    save_chat
)
from myllamacli.topics_contexts import generate_current_topic_summary, create_context_dict

from myllamacli.ui_shared import model_choice_setup, context_choice_setup
from myllamacli.ui_widgets_messages import QuestionAsk, FileSelected, SettingsChanged, IterationsScreenMessage
from myllamacli.ui_file_screen import FilePathScreen
from myllamacli.ui_settings_screen import SettingsScreen
from myllamacli.ui_modal_screens import QuitScreen, IterationsScreen

# CONSTANT PROMPTS
from myllamacli.prompts import DO_NOT_MAKEUP, EVALUATION_QUESTION, EVALUTATE_CONTEXT

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
        self.context_choice_id = self.load_current_context_id()
        self.context_choice_text = self.load_current_context_text()
        self.followup_model_choice_id  = ""
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

        #display
        self.model_date_display_info = ""

        # iterations screen
        self.iteration_count = 0
        self.model_info_as_string = ""

        # settings window
        self.settings_edit_selector = ""
        self.context_switcher_file_or_export = ""
        self.model_to_delete = ""

    ###### setup inits by calling database ########
    def load_get_current_settings(self):
        return CLI_Settings.get_by_id(1)
    
    def load_current_model(self):
        return LLM_MODEL.get_by_id(self.load_get_current_settings().llm_model_id)

    def load_current_context_id(self):
        return Context.get_by_id(self.load_get_current_settings().context_id).id

    def load_current_context_text(self):
        return Context.get_by_id(self.load_get_current_settings().context_id).text + DO_NOT_MAKEUP

    ######## GUI ##########
    def compose(self) -> ComposeResult:
        """ setup GUI for Application. """

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
                model_choice_setup(), prompt="Choose Primary Model:", id="ModelDisplay_topbar"
            )
            yield Button(
                f"Iterations: {self.iteration_count}",
                id="iterations_mainscreen",
                variant="primary",
                classes="ModelDisplay_topbar",
            )
            yield VerticalScroll(id="CurrentChant_MainChatWindow")
            yield Select(
                iter(
                    (sort_choice, sort_choice) for sort_choice in ["Topics", "Dates"]
                ),
                prompt="Sort Chats By:",
                id="ChatHistorySelect_topright",
            )
            yield Tree("Previous Chats", id="ChatHistoryDisplay_sidebar")
            yield QuestionAsk(id="QuestionAsk_bottombar")
            yield Button("Add File", id="filepathbutton", variant="primary")
            yield Button("Export Chats", id="export", variant="default")
        yield Footer()

    #############################
    #### Widget Helper Defs ####
    #############################

    def add_wdg_to_scroll(
        self, question, answer, model_name, previouschatdate
    ):
        """Create and mount widgets for chat"""
        chatcontainer = self.query_one("#CurrentChant_MainChatWindow")
        # Now Poulte question header
        model_date = Label(f"{str(model_name)} - ")

        # mount date and model info
        if previouschatdate is not None:
            qdate = previouschatdate
        else:
            qdate = "Today"

        model_date_display_info = f"{str(model_name)} - {qdate}"
        #chatcontainer.mount(model_date)
        
        # mount to chat container
        if question != EVALUATION_QUESTION:
            question_container = Markdown(question, classes="cssquestion")

        else:
            question_container = Markdown("Evaluation:",  classes="cssquestion")
      
        # add to question group 
        #chatcontainer.mount(model_date, question_container)
        logging.info(model_date_display_info)
        logging.info(self.model_date_display_info)

        if model_date_display_info != self.model_date_display_info:
            self.model_date_display_info = f"{str(model_name)} - {qdate}"
        
        chatcontainer.mount(Label(self.model_date_display_info , classes="cssdate"))
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


    def populate_tree_view(self, history_sort_choice) -> Dict:
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

    def update_tree(self, tree):
        """Update tree with selections from the DB"""
        logging.debug("sort choice: {}".format(self.chat_sort_choice))
        tree.clear()
        old_chats = tree.root.expand()
        old_chat_list = self.populate_tree_view(self.chat_sort_choice)
        for old_chat in old_chat_list:
            old_chats.add_leaf(old_chat)
        old_chats.add_leaf("New Chat")
        return tree

    def revision_model_selection(self):
        revision_model_name = self.followup_model_choice_name
        revision_model_id = self.followup_model_choice_id
        if (revision_model_id == "" or revision_model_id == Select.BLANK):
            revision_model_name = self.model_choice_name
            revision_model_id = self.model_choice_id
        return revision_model_name, revision_model_id

    ### this is the main wrapper for the chat ####
    async def chat_record_display(self, url: str, question: str, context: str, messages: list, model_name: str, model_id: str, file_path: str) -> None:
        """ Wraps chat call, saving to db, and displaying"""
        # chat
        answer, self.LLM_MESSAGES = await chat_with_llm_UI(
            url,
            question,
            context,
            messages,
            model_name,
            file_path,
        )

        # record
        chat_object_id = save_chat(question, answer, self.context_choice_id, self.topic_id, model_id)

        # add to list for topic updates later
        self.chat_object_list.append(chat_object_id)

        # display
        self.add_wdg_to_scroll(question, answer, model_name, None)


    #################################
    ##### ACTIONS | Main Window #####
    #################################
    @on(Select.Changed, "#ContextDisplay_topbar")
    def context_select_changed(self, event: Select.Changed) -> None:
        """ Get Selection from Context select box. """
        logging.debug("context_choice:{}".format(event))
        self.context_choice_id = str(event.value)
        context_obj = Context.get_by_id(str(event.value))
        context_text = context_obj.text
        self.context_choice_text = context_text

    @on(Select.Changed, "#ModelDisplay_topbar")
    def select_model_changed(self, event: Select.Changed) -> None:
        """ Get Selection from Model select box. """
        self.model_choice_id = str(event.value)
        logging.debug("Model: {}".format(self.model_choice_id))
        model_obj = LLM_MODEL.get_by_id(self.model_choice_id)
        self.model_choice_name = model_obj.model
        logging.debug("Model name: {}".format(self.model_choice_name))

    @on(Select.Changed, "#ModelFollowup_topbar")
    def select_model_changed(self, event: Select.Changed) -> None:
        """ Get Selection from Model select box. """
        self.followup_model_choice_id = str(event.value)
        logging.debug("Model: {}".format(self.model_choice_id))
        model_obj = LLM_MODEL.get_by_id(self.model_choice_id)
        self.followup_model_choice_name = model_obj.model
        logging.debug("Model name: {}".format(self.followup_model_choice_name))

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

        # setup question
        input = self.query_one("#question_text")
        question = input.value

        # setup loading graphic
        self.query_one("#SubmitQuestion").loading = True
        input.loading = True

        # call LLM 
        logging.debug("questions: {}".format(question))
        await self.chat_record_display(self.url, question, self.context_choice_text, self.LLM_MESSAGES, self.model_choice_name, self.model_choice_id, self.file_path)
        
        # clean up file path as the data will already be in messages
        self.file_path = ""

        if self.chats_loaded == False and self.iteration_count > 0:
            # this should be a call with a return
            revision_model_name, revision_model_id = self.revision_model_selection()
  
            for i in range(self.iteration_count):
                logging.info(f"{self.followup_model_choice_id} set as followup. Evaluating update.")
                self.notify(
                    "Evaluating and Updating previous answer", severity="information"
                )
                # note I'm saving chat with original context
                await self.chat_record_display(self.url, EVALUATION_QUESTION, EVALUTATE_CONTEXT, self.LLM_MESSAGES, revision_model_name, revision_model_id, self.file_path)

        # clean up after chat is complete
        self.done_loading()
        input.clear()
        self.chats_loaded = False


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
                previous_chat_date = chatdate[0]

                # get model id
                llm_model =LLM_MODEL.get_by_id(chat.llm_model_id)

                self.add_wdg_to_scroll(question, answer, llm_model.model, previous_chat_date)

            reformatted_previous_chats, self.topic_id = resume_previous_chats_ui(previous_chats)
            self.LLM_MESSAGES = self.LLM_MESSAGES + reformatted_previous_chats
            self.chat_object_list = list(previous_chats)
            self.chats_loaded = True


    @on(Button.Pressed, "#settings")
    def add_settings_screen_to_stack(self, event: Button.Pressed) -> None:
        logging.debug("settings")
        self.push_screen(SettingsScreen(self.url))


    @on(Button.Pressed, "#iterations_mainscreen")
    def add_interations_screen_to_stack(self, event: Button.Pressed) -> None:
        logging.debug("settings")
        self.push_screen(IterationsScreen(self.iteration_count, self.model_info_as_string))


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
            self.query_one("#ModelFollowup_topbar").set_options(model_choice_setup())

        if message.url_changed != "":
            self.url = message.url_changed


        ###### THIS IS NOT WORKING ####
    def on_iterations_screen_message(self, message: IterationsScreenMessage):        
        logging.info("iteracitons_selections caught")
        logging.info(message.interations_count)
        logging.info(message.model_info_stringlist)
        
        #self.iteration_count = message.interations_count
        #logging.info(self.iteration_count)

        # will need to unpack this
        #self.model_info_as_string = message.model_info_stringlist
        #logging.info(self.model_info_as_string)


    ##### TO DO add a init section ####
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