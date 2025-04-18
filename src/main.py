import logging

from datetime import datetime

from peewee import *
from textual import on  # , work
from textual.app import App, ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
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
    export_chat_as_file_ui,
    resume_previous_chats_ui
)
from src.myllamacli.topics_contexts import generate_current_topic_summary, create_context_dict
from src.myllamacli.llm_models import (
    pull_model,
    delete_llm_model,
    get_raw_model_list,
    add_model_if_not_present,
    align_db_and_ollama,
)

from src.myllamacli.ui_shared import model_choice_setup, context_choice_setup
from src.myllamacli.ui_screens_widgets import SettingsScreen, FilePathScreen, QuitScreen, QuestionAsk


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

    # reactives
    updated_url = reactive("")

    def __init__(self):
        """ Custom init for app"""
        super().__init__()
        # main window
        ##### at start pull in the settings from the DB ####
        self.url = self.load_get_current_settings().url #self.load_current_url()
        self.chat_sort_choice = "topics"
        self.model_choice_id = self.load_current_model().id
        self.model_choice_name = self.load_current_model().model
        self.context_choice_id = self.load_current_context().id
        self.context_choice_text = self.load_current_context().text
        self.topic_id = 1
        self.chats_loaded = False

        # Files
        self.isdir = False
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
        self.updated_url = self.url

        """Create child widgets for the app."""
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
                    (sort_choice, sort_choice) for sort_choice in ["Topics", "Contexts"]
                ),
                prompt="Sort Chats By:",
                id="ChatHistorySelect_topright",
            )
            yield VerticalScroll(id="CurrentChant_MainChatWindow")
            yield Tree("Chat History", id="ChatHistoryDisplay_sidebar")
            yield QuestionAsk(id="QuestionAsk_bottombar")
            yield Button("Add File", id="filepathbutton", variant="primary")
            yield Button("Export Chats", id="export", variant="default")
        yield Footer()

    #############################
    #### Widget Helper Defs ####
    #############################

    def update_tree(self, tree):
        """Update tree with selections from the DB"""
        logging.debug("sort choice: {}".format(self.chat_sort_choice))
        tree.clear()
        old_chats = tree.root.expand()
        # old_chats = tree.root.add("Chat History", expand=True)
        old_chat_list = populate_tree_view(self.chat_sort_choice)
        for old_chat in old_chat_list:
            old_chats.add_leaf(old_chat)
        old_chats.add_leaf("New Chat")
        return tree

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

    #################################
    ##### ACTIONS | Main Window #####
    #################################
    async def on_tree_node_selected(self, event: Tree) -> None:
        """Load Old Chats in tree. If new just, save existing and clear."""
        if len(self.chat_object_list) > 0:
            logging.info("saving chats")
            await self.action_save()
            self.chat_object_list = []
        choice_num = event.node.id + 1
        logging.debug("Tree label and id selected: {0}, {1}".format(event.node.label, choice_num))

        if event.node.label == "New Chat":
            # reset to default topic id
            self.topic_id = 1
        else:
            if self.chat_sort_choice == "topics":
                previous_chats = Chat.select().where(Chat.topic_id == choice_num)
            else:
                # self.chat_sort_choice == "contexts":
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

    # Filepath and File export buttons
    @on(Button.Pressed, "#export")
    @on(Button.Pressed, "#filepathbutton")
    def addfile_button_changed(self, event: Button.Pressed) -> None:
        """ Handle File buttons in the Main Window """
        if event.button.id == "filepathbutton":
            logging.debug("filepathbutton")
            self.isdir = False
            self.push_screen(FilePathScreen("hidden"))

        elif event.button.id == "export":
            logging.debug("export")
            self.isdir = True #because its a dir
            self.update_display = "visible"
            self.push_screen(FilePathScreen("visible"))

    ###############################################
    ### ACTIONS | FILE SELECTORS FilePathScreen ###
    ###############################################

    ##### close buttons for file, moving to filescressn class

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

            if len(self.LLM_MESSAGES) > 0:
                export_chat_as_file_ui(export_path, self.chat_object_list, code_only)
                self.notify("Chats Exported")
            else: 
                self.notify("No Chats to export, chat a bit then try again.")
            self.pop_screen()

    @on(DirectoryTree.FileSelected)
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        """ Handles tree when importing a file"""
        if not self.isdir:
            logging.debug(f"file: {event.path}")
            self.file_path = event.path
            self.pop_screen()

    @on(DirectoryTree.DirectorySelected)
    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected):
        """ Handles tree when choosing Dir for saving"""
        if self.isdir:  
            logging.debug(f"directory: {event.path}")
            self.directory_path = event.path


    ####################################
    ##### ACTIONS | Settings Window ####
    ####################################
    @on(Button.Pressed, "#settings")
    def add_settings_screen_to_stack(self, event: Button.Pressed) -> None:
        logging.debug("settings")
        self.push_screen(SettingsScreen())

    # close settings screen moving to settings class

    @on(Select.Changed, "#SettingsSelector")
    def select_changed(self, event: Select.Changed) -> None:
        self.settings_edit_selector = str(event.value)
        logging.debug("Settings Selector: {}".format(self.settings_edit_selector))
        self.query_one("#content_switcher_settings").current = self.settings_edit_selector.replace(
            " ", ""
        )
        if self.settings_edit_selector == "Edit URL":
            self.updated_url = self.url
            self.query_one("#CurrentUrl").update(f"Current Url: {self.updated_url}")

    #### URL ####
    @on(Button.Pressed, "#UpdateUrl")
    def updateurl_button_changed(self, event: Button.Pressed) -> None:
        logging.debug("UpdateUrl")
        input = self.query_one("#inputurl")
        self.url = input.value
        self.updated_url = self.url
        self.query_one("#CurrentUrl").update(f"Current Url: {self.updated_url}")

        currentsettings = CLI_Settings.get_by_id(1)
        currentsettings.url = self.url
        currentsettings.save()

        logging.debug(self.url)
        self.notify("URL Updated. Click Close Settings to return to Chat.")
        # default for ollama is http://localhost:11434

    #### Context Settings ####
    @on(Button.Pressed, "#NewContext")
    async def new_context_button_changed(self, event: Button.Pressed) -> None:
        logging.debug("NewContext")
        input = self.query_one("#NewContextInput")
        logging.debug(input)
        new_context = input.value
        logging.debug(new_context)
        new_context_id = Context.create(text=str(new_context))
        self.notify("Context Added. Click Close Settings to return to Chat.")
        self.query_one("#ContextEditChoose").set_options(context_choice_setup())

        # Not sure why but this isn't working
        #self.query_one("#ContextDisplay_topbar").set_options(context_choice_setup())

        # this isn't updating. Cannot figure out why
        #self.run_worker(self.query_one("#ContextDisplay_topbar", Select).set_options(context_choice_setup()), exclusive=True)


    @on(Button.Pressed, "#EditContext")
    async def edit_context_button_changed(self, event: Button.Pressed) -> None:
        logging.debug("Edit Context Button Pressed")
        context_id = self.query_one("#ContextEditChoose")
        logging.debug(context_id.value)
        context_to_change = Context.get_by_id(context_id.value)
        input = self.query_one("#EditContextInput")
        updated_context_text = input.value
        logging.debug(updated_context_text)
        context_to_change.text = updated_context_text
        context_to_change.save()
        input.clear()
        self.notify("Context Updated. Click Close Settings to return to Chat.")

        # Not sure why but this isn't working
        #self.query_one("#ContextDisplay_topbar").set_options(context_choice_setup())

        # this isn't updating. Cannot figure out why
        #self.run_worker(self.query_one("#ContextDisplay_topbar", Select).set_options(context_choice_setup()), exclusive=True)


    #### Topic Settings ####
    @on(Button.Pressed, "#NewTopic")
    def new_topic_button_changed(self, event: Button.Pressed) -> None:
        input = self.query_one("#NewTopicInput")
        new_topic = input.value
        logging.debug("New Topic created: {0}".formt(new_topic))
        Topic.create(text=str(new_topic))
        # this isn't updating. Cannot figure out why
        self.notify("Topic Added. Click Close Settings to return to Chat.")

    @on(Button.Pressed, "#EditTopic")
    def edit_topic_button_changed(self, event: Button.Pressed) -> None:
        logging.debug("EditTopic Button Pressed")
        topic_id = self.query_one("#TopicEditChoose")
        logging.debug(topic_id.value)
        topic_to_change = Topic.get_by_id(topic_id.value)
        input = self.query_one("#EditTopicInput")
        topic_text = input.value
        logging.debug("Topic: {0} changed to: {1}".format(topic_to_change, topic_text))
        topic_to_change.text = topic_text
        topic_to_change.save()
        input.clear()
        self.notify("Topic Updated. Click Close Settings to return to Chat.")

    #### Model ####
    @on(Button.Pressed, "#PullModel")
    async def pull_model_button_pressed(self, event: Button.Pressed) -> None:
        self.notify(
            "Pulling Model. This might take a while.",
            severity="information",
        )
        stored_llm_models = LLM_MODEL.select()
        logging.debug("PullModel Button Pressed")
        input = self.query_one("#ModelInput")
        logging.info("pulling {}".format(input.value))
        pull_text = await pull_model(self.url, str(input.value))
        logging.debug(pull_text.text)
        if "success" in pull_text.text:
            # repull to model list for confirmation
            model_list = await get_raw_model_list(self.url)
            logging.debug(model_list)
            self.notify(
                "Model Pulled and set as model choice. Click Close Settings to return to Chat.",
                severity="information",
            )
            input.clear()
            # on first pull, replace placeholder with a real model
            if (
                "Temp_fake" in [sm.model for sm in stored_llm_models]
                and len(model_list["models"]) == 1
            ):
                to_replace = LLM_MODEL.get(LLM_MODEL.model == "Temp_fake")
                new_model = model_list["models"][0]
                to_replace.model = new_model["model"]
                to_replace.size = new_model["size"]
                to_replace.currently_available = True
                to_replace.save()

            add_model_if_not_present(model_list, stored_llm_models)
            align_db_and_ollama(model_list, stored_llm_models)

            # Not sure why but this isn't working
            #self.query_one("#ModelDisplay_topbar").set_options(model_choice_setup())
 

        else:
            logging.info("Pull failed. output:{0}".format(pull_text))
            self.notify("Something Went Wrong. Please check name", severity="error")

        # this isn't updating. Cannot figure out why
        #self.query_one("#ModelDisplay_topbar").set_options(model_choice_setup())

    @on(DataTable.CellSelected)
    def on_data_table_cell_selected(
        self,
        event: DataTable.CellSelected,
    ) -> None:
        model_list = [model.model for model in LLM_MODEL.select() if model.currently_available == True]
        selection = str(event.value)
        if f'{selection}' in model_list:
            self.query_one("#model_to_delete_label").update(f"To Delete: {selection}")
            self.model_to_delete = selection
        else:
            self.model_to_delete = ""
            self.query_one("#model_to_delete_label").update(f"To Delete: No Selection")


    #### Model ####
    @on(Button.Pressed, "#DeleteModel")
    async def delete_model_button_pressed(self, event: Button.Pressed) -> None:
        logging.debug("DeleteModel Button Pressed")
        if self.model_to_delete == "":
            logging.error("Delete: No selection made from Models")
        else:
            logging.debug("Deleting {}".format(self.model_to_delete))
            rtn = await delete_llm_model(self.url, self.model_to_delete)
            if rtn.status_code == 200:
                # Set as not available in db
                dbmodel_to_delete = LLM_MODEL.get(LLM_MODEL.model == self.model_to_delete)
                dbmodel_to_delete.currently_available = False
                dbmodel_to_delete.save()
                self.notify(
                    "Model Deleted. Click Close Settings to return to Chat.",
                    severity="information",
                )
            
            # Not sure why but this isn't working
            #self.query_one("#ModelDisplay_topbar").set_options(model_choice_setup())
            
            else:
                logging.error(
                    "Delete of model {0} failed. output:{1}".format(
                        dbmodel_to_delete.model
                    ),
                    rtn,
                )
                self.notify("Something Went Wrong. Please check log", severity="error")

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