import logging
import os

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    RadioSet,
    RadioButton,
    Static,
)

from myllamacli.import_export_files import parse_export_path, export_chat_as_file_ui
from myllamacli.ui_widgets_messages import FileSelected, FilteredDirectoryTree


class FilePathScreen(Screen):
    CSS = """
    .visible {
        opacity: 100;
    }
    
    .hidden {
        opacity: 0;
    }
    """

    def __init__(self, import_files: bool, chat_object_list: list) -> None:
        super().__init__()
        self.input_class = import_files
        self.chat_object_list = chat_object_list
        self.show_hidden = True
        self.path_choice = ""

    def compose(self) -> ComposeResult:
        if self.input_class == True:
            dtlbl = "Select File or Directory for import"
            show_export = "hidden"
        else:
            dtlbl = "Select Directory for export"
            show_export = "visible"

        yield Static("\n")
        yield Static("Click to Close Settings Window without a Path")
        yield Button("Close Settings", id="CloseTree", variant="primary")
        yield Static("\n")
        yield Label(dtlbl, id="dtreelabel")
        yield Checkbox("show hidden files?", id="show_hiddent_files")
        yield FilteredDirectoryTree(path=parse_export_path("~", True), id="dirtree")
        yield Input(
            placeholder="Enter file name", id="FilePathInput", classes=show_export
        )
        with RadioSet(id="importexportradio", classes=show_export):
            yield RadioButton("Export Entire Chat", id="r1", value=True)
            yield RadioButton("Export Code Only", id="r2")
        yield Button("Import Files", id="submitpath", variant="primary")

    def on_mount(self) -> None:
        tree = self.query_one(FilteredDirectoryTree)
        tree.show_hidden = False

        submitbutton = self.query_one("#submitpath")

        if self.input_class:
            submitbutton.label = "Import Files"
        else:
            submitbutton.label = "Export Files"

    @on(Button.Pressed, "#CloseTree")
    def close_file_screen(self, event: Button.Pressed) -> None:
        """Handle buttons in close button in file screen."""
        logging.debug("CloseTree")
        self.dismiss()

    @on(Checkbox.Changed)
    def checkbox_changed(self, event: Checkbox.Changed) -> None:
        self.show_hidden = event.value
        tree = self.query_one("#dirtree", FilteredDirectoryTree)
        tree.show_hidden = self.show_hidden
        tree.reload()

    @on(Button.Pressed, "#submitpath")
    def submit_path_screen(self, event: Button.Pressed) -> None:
        """Handle buttons in filepath screen."""

        # export
        import_export_choice = self.query_one("#importexportradio").pressed_index
        logging.debug(f"radio: {import_export_choice}")

        # open file
        if self.input_class:
            dir_to_open = Path(self.path_choice).resolve()
            home_dir = Path.home().resolve()

            forbidden_subdirs = [home_dir / "Library", home_dir / "Applications"]

            allowed_mount_roots = [
                Path("/Volumes"),  # macOS
                Path("/mnt"),  # Linux
                Path("/media"),  # Linux
            ]

            is_in_home = False
            try:
                is_in_home = dir_to_open.relative_to(home_dir)
                is_in_home = True
            except ValueError:
                pass

            is_in_allowed_mount = any(
                root in dir_to_open.parents for root in allowed_mount_roots
            )
            is_in_forbidden_home = any(
                dir_to_open == p or p in dir_to_open.parents for p in forbidden_subdirs
            )

            if (is_in_home and not is_in_forbidden_home) or is_in_allowed_mount:
                self.post_message(FileSelected(str(self.path_choice)))
                self.dismiss()
            else:
                self.notify(
                    "Please limit scanning to your user home folder (except applications or Library) or mounts",
                    severity="Error",
                )

        # export files
        else:
            input = self.query_one("#FilePathInput")
            file_name = str(input.value)
            self.path_choice = self.path_choice + "/" + file_name
            logging.info(f"dir {self.path_choice}")

            logging.debug(f"export_toggle: {import_export_choice}")
            if import_export_choice == 1:
                code_only = True
                self.notify("Exporting Chat. Please wait.")
            else:
                code_only = False
                self.notify("Exporting Code examples from Chat. Please wait.")
            if len(self.chat_object_list) > 0:
                logging.debug(
                    f"exporting {self.chat_object_list} to: {self.path_choice}"
                )
                export_chat_as_file_ui(
                    self.path_choice, self.chat_object_list, code_only
                )
                self.notify("Chats Exported")
            else:
                self.notify("No Chats to export, chat a bit then try again.")

    @on(FilteredDirectoryTree.FileSelected)
    def on_directory_tree_file_selected(
        self, event: FilteredDirectoryTree.FileSelected
    ) -> None:
        """Handles tree when importing a file"""
        logging.debug(f"directory: {event.path}")
        if self.input_class == True:
            self.path_choice = str(event.path)
            logging.debug(f"file {self.path_choice}")

    @on(FilteredDirectoryTree.DirectorySelected)
    def on_directory_tree_directory_selected(
        self, event: FilteredDirectoryTree.DirectorySelected
    ) -> None:
        """Handles tree when choosing Dir for saving"""
        logging.debug(f"directory: {event.path}")
        self.path_choice = str(event.path)
