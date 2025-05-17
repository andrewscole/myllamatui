import logging

from peewee import *

from textual import on
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Label, Select


from src.myllamacli.db_models import LLM_MODEL
from src.myllamacli.ui_shared import model_choice_setup


# Modal screens
class QuitScreen(ModalScreen):
    """Shows warning that I am qutting"""

    CSS = """
    QuitScreen {
        align: center middle;
    }
    """

    def __init__(self, qs_message: str) -> None:
        super().__init__()
        self.qs_message = qs_message

    def compose(self) -> ComposeResult:
        yield Label(self.qs_message, id="qa_savingmessage", classes="ModelIteration")
