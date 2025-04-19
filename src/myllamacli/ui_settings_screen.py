import logging

from textual import on
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from src.myllamacli.db_models import LLM_MODEL, Chat, Context, Topic
from src.myllamacli.ui_shared import model_choice_setup, context_choice_setup, create_topics_select
from src.myllamacli.ui_modal_and_widgets import SettingsChanged


class SettingsScreen(Screen):
    updated_url = reactive("")

    # might not need this
    def __init__(self):
        super().__init__()
        self.close_message = ""
        self.dbmodels = {"model_select": "False", "topic_select": "False", "context_select": "False"}

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

    #@on(Select.Changed, "#SettingsSelector")
    #def select_changed(self, event: Select.Changed) -> None:
    #    self.settings_edit_selector = str(event.value)
    #    logging.debug("Settings Selector: {}".format(self.settings_edit_selector))
    #    self.query_one("#content_switcher_settings").current = self.settings_edit_selector.replace(
    #        " ", ""
    #    )
    #    if self.settings_edit_selector == "Edit URL":
    #        self.updated_url = self.url
    #        self.query_one("#CurrentUrl").update(f"Current Url: {self.updated_url}")

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
        self.dbmodels["context_select"] = True


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
        self.dbmodels["context_select"] = "True"

    #### Topic Settings ####
    @on(Button.Pressed, "#NewTopic")
    def new_topic_button_changed(self, event: Button.Pressed) -> None:
        input = self.query_one("#NewTopicInput")
        new_topic = input.value
        logging.debug("New Topic created: {0}".format(new_topic))
        Topic.create(text=str(new_topic))
        # this isn't updating. Cannot figure out why
        self.notify("Topic Added. Click Close Settings to return to Chat.")
        self.dbmodels["topic_select"] = "True"

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
        self.dbmodels["topic_select"] = "True"

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
            self.dbmodels["model_select"] = "True"

        else:
            logging.info("Pull failed. output:{0}".format(pull_text))
            self.notify("Something Went Wrong. Please check name", severity="error")


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
                self.dbmodels["model_select"] = "True"
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

    @on(Button.Pressed, "#CloseSetting")
    def close_settings_screen(self, event: Button.Pressed) -> None:
        logging.debug("CloseSetting")
        logging.info(f"from settings {self.dbmodels}")
        self.post_message(SettingsChanged(self.dbmodels["context_select"], self.dbmodels["topic_select"], self.dbmodels["model_select"]))
        self.dismiss()
