import httpx
import pytest

from unittest.mock import patch, MagicMock, AsyncMock

from src.myllamacli.setup_utils import (
    initialize_db_defaults,
    create_db,
    create_temp_fake_model,
    read_add_models,
    CLI_DEFAULTS,
)
from src.myllamacli.db_models import Context, Category, Topic, LLM_MODEL, CLI_Settings

from src.myllamacli.llm_models import (
    parse_model_list,
    get_raw_model_list,
    post_action_to_model_manager,
    delete_llm_model,
    pull_and_parse_model_capabilities,
    parse_model_name_for_skill,
    get_model_capabilities,
    add_model_if_not_present,
    align_db_and_ollama,
)




# Mocking database models
class MockContext:
    def __init__(self, text):
        self.text = text

    @classmethod
    def create(cls, text):
        return cls(text)

class MockCategory:
    def __init__(self, text):
        self.text = text

    @classmethod
    def create(cls, text):
        return cls(text)

class MockTopic:
    def __init__(self, text, category_id):
        self.text = text
        self.category_id = category_id

    @classmethod
    def create(cls, text, category_id):
        return cls(text, category_id)

class MockLLM_MODEL:
    def __init__(self, model, specialization, size, currently_available):
        self.model = model
        self.specialization = specialization
        self.size = size
        self.currently_available = currently_available

    @classmethod
    def create(cls, model, specialization, size, currently_available):
        return cls(model, specialization, size, currently_available)

class MockCLI_Settings:
    def __init__(self, url, context_id, topic_id, llm_model_id):
        self.url = url
        self.context_id = context_id
        self.topic_id = topic_id
        self.llm_model_id = llm_model_id

    @classmethod
    def create(cls, url, context_id, topic_id, llm_model_id):
        return cls(url, context_id, topic_id, llm_model_id)

def confirm_test_database():
    assert llm_model._meta.database.database == ':memory:'


# Mocking asynchronous functions
async def mock_get_raw_model_list(url):
    return {"models": [{"model": "Model 1", "size": 1024}]}

async def mock_get_model_capabilities(url, model_name):
    return "specialization"


def test_create_temp_fake_model(test_database, mock_llm_model):
    create_temp_fake_model()
    assert LLM_MODEL.get_or_create(model="Temp_fake", specialization="general", size=0, currently_available=True) is not None


@pytest.mark.asyncio
async def test_read_add_models_with_models(test_database, mock_get):
    url = "http://localhost:11434"
    raw_model_list = {"models": [{"name": "visionmodel1"}, {"name": "genericmodel2"}]}
    mock_get.return_value = httpx.Response(status_code=200, json=raw_model_list)
    await read_add_models(url)
    assert LLM_MODEL.create(model="visionmodel1", specialization="vision", size=1024, currently_available=True) is not None

@pytest.mark.asyncio
async def test_read_add_models_no_models(test_database, mock_get):
    url = "http://localhost:11434"
    raw_model_list = {"models": []}
    mock_get.return_value = httpx.Response(status_code=200, json=raw_model_list)
    await read_add_models(url)
    models = LLM_MODEL.select()
    for model in models:
        assert model.model == "Temp_fake"

def test_create_db(test_database):
    # Call the function
    create_db()
    
    model = LLM_MODEL.create(model="alice", size=1, specialization="general", currently_available=True)
    result = User.get(User.username == "alice")
    assert result.username == "alice"


##### failing ####
@pytest.mark.asyncio
async def initialize_db_defaults(test_database):
        await setup_db_and_initialize_defaults()
        assert len(Context.select()) == 2

        # Verify that contexts are created
        assert MockContext.create(text="You are a friendly and helpful assistant, always aiming to provide informative and comprehensive answers.") is not None
        assert MockContext.create(text="You are a friendly Senior Developer assisting a jounior developer by providing code examples and comprehensive explanations.") is not None

        # Verify that categories are created
        assert MockCategory.create(text="default") is not None
        assert MockCategory.create(text="Jokes") is not None
        assert MockCategory.create(text="Python") is not None
        assert MockCategory.create(text="Ruby") is not None
        assert MockCategory.create(text="Software Design") is not None
        assert MockCategory.create(text="AWS") is not None
        assert MockCategory.create(text="Historical Figures") is not None

        # Verify that topics are created
        assert MockTopic.create(text="default", category_id=1) is not None
        assert MockTopic.create(text="Dad Jokes", category_id=2) is not None
        assert MockTopic.create(text="Python Textual", category_id=3) is not None

        # Verify that CLI settings are created
        assert MockCLI_Settings.create(
            url=CLI_DEFAULTS["url"],
            context_id=CLI_DEFAULTS["context_id"],
            topic_id=CLI_DEFAULTS["topic_id"],
            llm_model_id=CLI_DEFAULTS["llm_model_id"],
        ) is not None

# Run the tests with pytest
if __name__ == "__main__":
    pytest.main()
