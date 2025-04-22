import logging

from peewee import *

from textual import on
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    Label,
    Select
)


from myllamacli.db_models import LLM_MODEL
from myllamacli.ui_shared import model_choice_setup
from myllamacli.ui_widgets_messages import SettingsChanged, IterationsScreenMessage

# Modal screens
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
        yield Label(self.qs_message, id="qa_savingmessage", classes="ModelIteration")


class IterationsScreen(ModalScreen):
    """Allows me to set the #of iterations I want"""

    CSS = """
    ModelIteration {
        align: center middle;
    }
    """
    def __init__(self, count, model_info_as_string):
        super().__init__()
        self.count = count
        self.model_info_as_string = model_info_as_string

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="model_iteration_container")
        yield Button("Add Iteration", id="add_model_iteration", variant="primary")
        yield Button("Submit and Close", id="CloseIterations", variant="success")

    #actions
    @on(Button.Pressed, "#add_model_iteration")
    def add_iteration_button(self, event: Button.Pressed) -> None:
        """ Get Selection from Model select box. """
        self.count += 1
        veiwcontainer = self.query_one("#model_iteration_container")
        
        modelselect = Select(
                model_choice_setup(), prompt=f"Choose Model for followup #{self.count}:", id=f"modelselect{self.count}"
            )
        veiwcontainer.mount(modelselect)

    # this needs a way to differentiate between instances
    @on(Select.Changed)
    def select_model_changed(self, event: Select.Changed) -> None:
        """ Get Selection from Model select box. """
        logging.info(event)
        model_choice_id = str(event.value)
        model_obj = LLM_MODEL.get_by_id(model_choice_id)
        model_choice_name = model_obj.model
        # I need to do this due to the limiations of the messages
        model_info_as_string = f"{self.count}" + ":" "[{model_choice_name}, {model_choice_id}]"
        if self.count == 0:
            self.model_info_as_string = model_info_as_string
        else:
            self.model_info_as_string = self.model_info_as_string + ", " + model_info_as_string



    @on(Button.Pressed, "#CloseIterations")
    def close_settings_screen(self, event: Button.Pressed) -> None:
        logging.debug("CloseIterations")
        self.post_message(IterationsScreenMessage(self.count, self.model_info_as_string))
        self.dismiss()