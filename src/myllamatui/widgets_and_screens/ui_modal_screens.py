import logging

from peewee import *

from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Select


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
