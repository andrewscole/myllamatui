import httpx
import pytest

from unittest.mock import patch, MagicMock, AsyncMock

from src.myllamatui.setup_utils import (
    initialize_db_defaults,
    create_db,
    create_temp_fake_model,
    populate_llm_models,
    CLI_DEFAULTS,
)
from src.myllamatui.db_models import (
    Category,
    Chat,
    Context,
    Topic,
    LLM_MODEL,
    CLI_Settings,
)


def test_create_temp_fake_model(test_database, mock_llm_model):
    create_temp_fake_model()
    assert (
        LLM_MODEL.get_or_create(
            model="Temp_fake",
            specialization="general",
            size=0,
            currently_available=True,
        )
        is not None
    )


@pytest.mark.asyncio
async def test_populate_llm_models_with_models(test_database, mock_get):
    raw_model_list = {"models": [{"name": "visionmodel1"}, {"name": "genericmodel2"}]}
    mock_get.return_value = httpx.Response(status_code=200, json=raw_model_list)
    await populate_llm_models()
    assert (
        LLM_MODEL.create(
            model="visionmodel1",
            specialization="vision",
            size=1024,
            currently_available=True,
        )
        is not None
    )


@pytest.mark.asyncio
async def test_populate_llm_models_no_models(test_database, mock_get):
    raw_model_list = {"models": []}
    mock_get.return_value = httpx.Response(status_code=200, json=raw_model_list)
    await populate_llm_models()
    models = LLM_MODEL.select()
    for model in models:
        assert model.model == "Temp_fake"


@patch("src.myllamatui.setup_utils.SQLITE_DB.connect")
@patch("src.myllamatui.setup_utils.SQLITE_DB.create_tables")
def test_create_db(mock_create_tables, mock_connect):
    # Call the function
    create_db()

    # Assertions to verify behavior
    mock_connect.assert_called_once()  # Verify connect is called once
    mock_create_tables.assert_called_once_with(
        [Context, Category, Topic, Chat, LLM_MODEL, CLI_Settings], safe=True
    )  # Verify correct table list


@pytest.mark.asyncio
async def test_initialize_db_defaults(test_database, mock_get):
    raw_model_list = {"models": []}
    mock_get.return_value = httpx.Response(status_code=200, json=raw_model_list)
    await populate_llm_models()
    initialize_db_defaults()

    # check tables
    # I could assert but I don't think its necessary
    assert LLM_MODEL._meta.database.database == ":memory:"
    assert Topic._meta.database.database == ":memory:"

    # context:
    context_1 = Context.get_by_id(1)
    context_2 = Context.get_by_id(2)
    assert len(Context.select()) == 2
    assert (
        context_1.text
        == "You are a friendly and helpful assistant, always aiming to provide informative and comprehensive answers."
    )
    assert (
        context_2.text
        == "You are a friendly senior developer assisting a jounior developer by providing code examples and comprehensive explanations."
    )

    # categories
    categories = [cat.text for cat in Category.select()]
    assert categories == [
        "default",
        "Jokes",
        "Python",
        "Ruby",
        "Software Design",
        "AWS",
        "Historical Figures",
    ]

    # topics
    topics = [top.text for top in Topic.select()]
    assert topics == ["default", "Dad Jokes", "Python Textual"]

    # check a default settings:
    defaults = CLI_Settings.get_by_id(1)
    assert defaults.url == "http://localhost:11434"
    assert str(defaults.context_id) == "1"
    assert str(defaults.topic_id) == "1"
    assert str(defaults.llm_model_id) == "1"
