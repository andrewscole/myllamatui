import os
import re

import pytest

from unittest import mock
from unittest.mock import patch, mock_open, Mock, MagicMock
from pathlib import Path

from src.myllamatui.db_models import Chat, LLM_MODEL, Topic, Category, Context
from src.myllamatui.widgets_and_screens.ui_widgets_messages import SupportNotifyRequest
from src.myllamatui.import_export_files import (
    open_file,
    open_files_in_dir,
    open_files_and_add_to_question,
    check_file_type,
    parse_export_path,
    export_text_file,
    export_code_file,
    export_chat_as_file_ui,
)


MOCK_FILE_CONTENT = "File contents."
MOCK_DIR_STRUCTURE = {
    "test_dir/file1.txt": "File 1 content",
    "test_dir/file2.txt": "File 2 content",
    "test_dir/.git/config": "Git config",
    "test_dir/.DS_Store": "",
    "test_dir/__pycache__/cache.pyc": "",
}


# helper defs
def create_test_chat(
    fake_model="general_model",
    fake_context="my fake context",
    fake_topic="my fake topic",
    fake_question="I have a question.",
    fake_answer="I have an answer.",
):
    test_model = LLM_MODEL.create(
        model=fake_model, size=34567, specialization="general", currently_available=True
    )
    test_context = Context.create(text=fake_context)
    test_category = Category.create(text="my test category")
    test_topic = Topic.create(text=fake_topic, category_id=test_category.id)
    test_chat = Chat.create(
        question=fake_question,
        answer=fake_answer,
        context_id=test_context.id,
        topic_id=test_topic.id,
        llm_model_id=test_model.id,
    )
    return test_chat


@pytest.fixture
def mock_open_write():
    with patch("builtins.open", new_callable=MagicMock) as mock_open_write:
        yield mock_open_write


def confirm_test_database():
    assert llm_model._meta.database.database == ":memory:"


# Open File
def test_open_file_success(tmp_path):
    # Create a temporary test file
    test_file = tmp_path / "test_file.txt"
    test_content = "Hello, world!"
    test_file.write_text(test_content)

    # Test the function
    result = open_file(str(test_file))

    # Verify the result
    assert result == test_content


def test_open_file_failure():
    # Test with a non-existent file
    result = open_file("non_existent_file.txt")

    # Verify the result
    assert result == "File Unproccessable"
    SupportNotifyRequest.content = "Unable to open file. nonexistent.txt"
    SupportNotifyRequest.severity = "warning"


def test_open_files_in_dir_with_files(tmp_path):
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("Content of file 1")
    file2.write_text("Content of file 2")

    # Test the function
    result = open_files_in_dir(str(tmp_path))

    # Verify results (order may vary)
    assert len(result) == 2
    assert "Content of file 1" in result
    assert "Content of file 2" in result


def test_open_files_in_dir_with_nested_files(tmp_path):
    # Create nested directory structure
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()

    file1 = tmp_path / "file1.txt"
    file2 = nested_dir / "file2.txt"
    file1.write_text("Content of file 1")
    file2.write_text("Content of file 2")

    # Test the function
    result = open_files_in_dir(str(tmp_path))

    # Verify results
    assert len(result) == 2
    assert "Content of file 1" in result
    assert "Content of file 2" in result


def test_open_files_in_dir_ignored_files(tmp_path):
    # Create ignored files
    ignored_dir = tmp_path / ".git"
    ignored_dir.mkdir()
    ignored_file = ignored_dir / "ignore_me.txt"
    ignored_file.write_text("This should be ignored")

    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("This should be included")

    ds_store = tmp_path / ".DS_Store"
    ds_store.write_text("This should be ignored")

    # Test the function
    result = open_files_in_dir(str(tmp_path))

    # Verify only regular file was included
    assert len(result) == 1
    assert "This should be included" in result
    assert "This should be ignored" not in result


# Tests for open_files_and_add_to_question function
def test_open_files_and_add_to_question_with_file():
    # Use standard library's mock with patch
    with mock.patch("os.path.isdir", return_value=False) as mock_isdir:
        with mock.patch(
            "src.myllamatui.import_export_files.open_file", return_value="File content"
        ) as mock_open_file:
            # Run the function
            result = open_files_and_add_to_question("Initial question", "path/to/file")

    # Verify result
    assert result == "Initial question. Here is my file: File content"
    mock_isdir.assert_called_once_with("path/to/file")
    mock_open_file.assert_called_once_with("path/to/file")


def test_open_files_and_add_to_question_with_directory():
    # Use standard library's mock with patch
    with mock.patch("os.path.isdir", return_value=True) as mock_isdir:
        with mock.patch(
            "src.myllamatui.import_export_files.open_files_in_dir",
            return_value=["File 1", "File 2"],
        ) as mock_open_files:
            # Run the function
            result = open_files_and_add_to_question("Initial question", "path/to/dir")

    # Verify result
    assert result == "Initial question. Here are my files: ['File 1', 'File 2']"
    mock_isdir.assert_called_once_with("path/to/dir")
    mock_open_files.assert_called_once_with("path/to/dir")


def test_open_files_and_add_to_question_integration(tmp_path):
    # Create a test file
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("Test content")

    # Run function with real file
    result = open_files_and_add_to_question("My question", str(test_file))

    # Verify result
    assert result == "My question. Here is my file: Test content"

    # Create a test directory with files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    file1 = test_dir / "file1.txt"
    file1.write_text("Content 1")

    # Run function with real directory
    result = open_files_and_add_to_question("My question", str(test_dir))

    # Verify result
    assert "My question. Here are my files: [" in result
    assert "Content 1" in result


# Optional: parametrize tests for more combinations
@pytest.mark.parametrize(
    "content,expected",
    [
        ("Simple content", "Simple content"),
        ("", ""),  # Empty file
        ("Multi\nline\ncontent", "Multi\nline\ncontent"),  # Multiline content
    ],
)
def test_open_file_parametrized(tmp_path, content, expected):
    # Create a temporary test file with parametrized content
    test_file = tmp_path / "param_test.txt"
    test_file.write_text(content)

    # Test the function
    result = open_file(str(test_file))

    # Verify the result
    assert result == expected


@pytest.mark.parametrize(
    "model_name, f_specialization, file_name, tf",
    [
        ("general_model", "general", "text.txt", True),
        ("general_model", "general", "pic.jpg", False),
        ("visual_model", "vision", "text.txt", True),
        ("visual_model", "vision", "pic.jpg", True),
    ],
)
def test_check_file_type(test_database, model_name, f_specialization, file_name, tf):
    """Test file type checking logic"""
    # Test photo file with vision model
    model_id = LLM_MODEL.create(
        model=model_name,
        size=34567,
        specialization=f_specialization,
        currently_available=True,
    )

    assert check_file_type(file_name, model_id) is tf


def test_parse_export_path():
    """Test path parsing logic"""
    # Test normal path
    result = parse_export_path("test_path")
    assert result == "test_path"

    # Test path with ~
    result = parse_export_path("~/.config/test")
    assert result == os.path.expanduser("~/.config/test")


def test_export_text_file(test_database, mock_open_write):
    """Test text file export"""
    result = create_test_chat(
        "FakeModel", "answer text", "test topic", "question text", "answer text"
    )

    with mock.patch(
        "src.myllamatui.import_export_files.open", mock_open_write()
    ) as mocked_open:
        export_text_file("test.txt", [result])
        mocked_open.assert_called_once_with("test.txt", "w")


def test_export_code_file(test_database, mock_open_write):

    answer_text = """
    FileSelector.py ```
    class FileSelectorApp(App):
    CSS_PATH = "file_selector.css"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select a file from the directory tree", id="title")
            with Horizontal(id="main-container"):
                yield DirectoryTree(path="/path/to/your/directory", id="directory-tree")
                yield Vertical(
                    Static("Selected File Path:", id="selected-file-path"),
                    Button("Get Path", id="get-path-button"),
                    Input(placeholder="Type something...", classes="hidden-input", id="input-widget")
                )
            yield Footer()```
    """

    result = create_test_chat(
        "FakeModel", "my fake context", "test topic", "question text", answer_text
    )

    with mock.patch(
        "src.myllamatui.import_export_files.open", mock_open_write()
    ) as mocked_open:
        with mock.patch("src.myllamatui.import_export_files.os") as mock_dir_write:
            export_code_file("test", [result])
            mocked_open.assert_called_once
            mock_dir_write.assert_called_once
