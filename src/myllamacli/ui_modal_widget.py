from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.screen import ModalScreen
from textual.message import Message
from textual.widgets import (
    Button,
    Input,
    Label
)


# message classes
class FileSelected(Message):
    def __init__(self, path: str):
        super().__init__()
        self.path = path


class SettingsChanged(Message):
    def __init__(self, context_changed: str, topic_changed: str, model_changed: str, url_changed: str):
        super().__init__()
        self.context_changed = context_changed
        self.topic_changed = topic_changed
        self.model_changed = model_changed
        self.url_changed = url_changed

# Modal screen
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
        
# widgets
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
