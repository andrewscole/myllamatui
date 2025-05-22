import pytest
import datetime

import httpx

from unittest.mock import AsyncMock, patch
from pathlib import Path

from peewee import *

from src.myllamatui.db_models import BaseModel, Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings

# List all models you want to test
TEST_MODELS = [Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings]

# Create an in-memory SQLite database
test_db = SqliteDatabase(':memory:')

@pytest.fixture(scope="function")
def test_database():
    original_databases = {model: model._meta.database for model in TEST_MODELS}

    # Temporarily rebind the models to the test DB
    test_db.bind(TEST_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(TEST_MODELS)

    for model in TEST_MODELS:
        model._meta.database = test_db

    # Swap out the original database on the base model
    #original_database = BaseModel._meta.database
    #BaseModel._meta.database = test_db

    yield  # Run the test

    test_db.drop_tables(TEST_MODELS)
    test_db.close()
    for model, original_db in original_databases.items():
        model._meta.database = original_db



# Mock the LLM_MODEL
class MockLLMModel:
    def __init__(self, id, specialization):
        self.id = id
        self.specialization = specialization
    
    @classmethod
    def get_by_id(cls, model_id):
        return MockLLMModel(model_id, "vision")  # Default to vision for testing

# Mock the Chat
class MockChat:
    def __init__(self, id, question, answer, context_id, topic_id, llm_model_id):
        self.id = id
        self.question = question
        self.answer = answer
        self.context_id = context_id
        self.topic_id = topic_id
        self.llm_model_id = llm_model_id
        self.created_at = DateTimeField(default=datetime.now)  

    @classmethod
    def get_by_id(cls, chat_id):
        return MockChat(chat_id, "1")

    def update_chat_topic_from_summary(topic_id):
        return MockChat(topic_id, "1")

class MockContext:
    def __init__(self, text):
        self.text = text

    @classmethod
    def select(cls):
        return [cls("Context 1"), cls("Context 2")]


class MockTopic:
    def __init__(self, text):
        self.text = text

    @classmethod
    def select(cls):
        return [cls("Topic 1"), cls("Topic 2")]


class MockCategory:
    def __init__(self, text):
        self.text = text

    @classmethod
    def select(cls):
        return [cls("Category 1"), cls("Category 2")]


@pytest.fixture
def mock_llm_model():
    with patch('src.myllamatui.db_models.LLM_MODEL', new=MockLLMModel):
        yield

@pytest.fixture
def mock_topic():
    with patch('src.myllamatui.db_models.Topic', new=MockTopic):
        yield

@pytest.fixture
def mock_context():
    with patch('src.myllamatui.db_models.Context', new=MockContext):
        yield

@pytest.fixture
def mock_chat():
    with patch('src.myllamatui.db_models.Chat', new=MockChat):
        yield

@pytest.fixture
def mock_path():
    with patch('pathlib.Path') as mock_path:
        yield mock_path

@pytest.fixture
def mock_logging():
    with patch('logging.info') as mock_logging:
        with patch('logging.debug') as mock_logging_debug:
            yield mock_logging, mock_logging_debug

@pytest.fixture
def mock_get():
    """Fixture to mock httpx.AsyncClient.get method."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_post():
    """Fixture to mock httpx.AsyncClient.post method."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_delete():
    """Fixture to mock httpx.AsyncClient.post method."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock:
        yield mock