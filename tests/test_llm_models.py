import json

import pytest
import httpx

from unittest.mock import patch, AsyncMock

# Import your functions from the module you want to test
from src.myllamatui.llm_models import (
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

# Mock the functions from your dependencies
from src.myllamatui.llm_calls import (
    generate_endpoint, 
    generate_data_for_model_pull,
)

# Mock the database models
from src.myllamatui.db_models import LLM_MODEL


def confirm_test_database():
    assert llm_model._meta.database.database == ':memory:'


# Test parse_model_list
def test_parse_model_list():
    raw_model_list = {
        "models": [
            {"name": "model1"},
            {"name": "model2"}
        ]
    }
    expected_output = ["model1", "model2"]
    assert parse_model_list(raw_model_list) == expected_output

# Test parse_model_name_for_skill
def test_parse_model_name_for_skill():
    model_name = "model_code"
    expected_output = "coding"

    result = parse_model_name_for_skill(model_name)
    assert result == expected_output

# Test get_model_capabilities
@pytest.mark.asyncio
async def test_get_model_capabilities_in_name():
    url = "http://example.com"
    model_name = "visionmodel"
    expected_output = "vision"
    result = await get_model_capabilities(url, model_name)
    assert result == expected_output


# Test get_model_capabilities
@pytest.mark.parametrize(
    "mock_skill,mock_result",
    [
        ("tools", "general"),
        ("general", "general"), 
        ("completion", "general"), 
        ("insert", "general"),
        ("vision", "vision"),
        ("reasoning", "reasoning"),
    ],
)
@pytest.mark.asyncio
async def test_get_model_capabilities_not_in_name(mock_post, mock_skill, mock_result):
    url = "http://example.com"
    model_name = "model1"

    mock_post.return_value = httpx.Response(status_code=200, json={"capabilities": [mock_skill]})
    result = await get_model_capabilities(url, model_name)
    assert result == mock_result

# Test get_raw_model_list
@pytest.mark.asyncio
async def test_get_raw_model_list(mock_get):
    url = "http://example.com"
    raw_model_list = {"models": [{"name": "model1"}, {"name": "model2"}]}
    apiendpoint = generate_endpoint(url, "show_list")



    mock_get.return_value = httpx.Response(status_code=200, json=raw_model_list)
    result = await get_raw_model_list(url)
    assert result == raw_model_list
    mock_get.assert_called_once_with(apiendpoint, timeout=300.0)


@pytest.mark.asyncio
async def test_post_action_to_model_manager(mock_post):
    url = "http://example.com"
    model = "model1"
    action = "pull"
    expected_output = "pull_text"

    
    apiendpoint = generate_endpoint(url, action)
    data = generate_data_for_model_pull(model)
    
    mock_post.return_value = httpx.Response(status_code=200, text=expected_output)
    result = await post_action_to_model_manager(url, model, action)
    print(result)
    assert result.text == expected_output
    mock_post.assert_called_once_with(apiendpoint, json=data, timeout=900.0)


# Test delete_llm_model
@pytest.mark.asyncio
async def test_delete_llm_model(mock_delete):
    url = "http://example.com"
    model = "model1"
    expected_output = "delete_text"

    apiendpoint = generate_endpoint(url, "delete")
    data = generate_data_for_model_pull(model)


    mock_delete.return_value = httpx.Response(status_code=200, text=expected_output)

    result = await delete_llm_model(url, model)
    assert result.text == expected_output
    mock_delete.assert_called_once_with(method='DELETE', url='http://example.com/api/delete', json={'model': 'model1'}, timeout=300.0)


@pytest.mark.parametrize(
    "mock_skill,mock_result",
    [
        ("tools", "general"),
        ("general", "general"), 
        ("completion", "general"), 
        ("insert", "general"),
        ("vision", "vision"),
        ("reasoning", "reasoning"),
    ],
)
@pytest.mark.asyncio
async def test_pull_and_parse_model_capabilities(mock_post, mock_skill, mock_result):
    url = "http://example.com"
    model_name = "model1"
    action = "model_info"
    
    apiendpoint = generate_endpoint(url, action)
    data = generate_data_for_model_pull(model_name)
    

    mock_post.return_value = httpx.Response(status_code=200, json={"capabilities": [mock_skill]})

    result = await pull_and_parse_model_capabilities(url, model_name)
    assert result == mock_result
    mock_post.assert_called_once_with(apiendpoint, json=data, timeout=900.0)


# Test add_model_if_not_present
def test_add_model_if_not_present_new_model(test_database):
    ollama_list = {
        "models": [
            {"model": "model1", "size": 1, "specialization": "general"},
            {"model": "model2", "size": 2, "specialization": "vision"}

        ]
    }

    for model in ollama_list["models"]:
        LLM_MODEL.get_or_create(
            model=model["model"],
            specialization=model["specialization"],
            size=model["size"],
            currently_available=True,
        )

    ollama_list["models"].append({"model": "model3", "size": 3, "specialization": "general"})
    # add models
    ollama_names = []
    for model in ollama_list["models"]:
        ollama_names.append(model["model"])

    stored_llm_models = LLM_MODEL.select()

    stored_names = []
    for model in stored_llm_models:
        stored_names.append(model.model)

    assert ollama_names != stored_names


    add_model_if_not_present(ollama_list, stored_llm_models)

    stored_llm_models = LLM_MODEL.select()

    stored_names = []
    for model in stored_llm_models:
        stored_names.append(model.model)
    
    assert ollama_names == stored_names



# Test add_model_if_not_present
def test_add_model_no_change_no_new_model(test_database):
    ollama_list = {
        "models": [
            {"model": "model1", "size": 1, "specialization": "general"},
            {"model": "model2", "size": 2, "specialization": "vision"}

        ]
    }

    for model in ollama_list["models"]:
        LLM_MODEL.get_or_create(
            model=model["model"],
            specialization=model["specialization"],
            size=model["size"],
            currently_available=True,
        )

    # add models
    ollama_names = []
    for model in ollama_list["models"]:
        ollama_names.append(model["model"])

    stored_llm_models = LLM_MODEL.select()

    stored_names = []
    for model in stored_llm_models:
        stored_names.append(model.model)

    assert ollama_names == stored_names


    add_model_if_not_present(ollama_list, stored_llm_models)

    stored_llm_models = LLM_MODEL.select()

    stored_names = []
    for model in stored_llm_models:
        stored_names.append(model.model)
    
    assert ollama_names == stored_names



    # Add your assertions here to check if new models are added correctly

# Test align_db_and_ollama
def test_align_db_and_ollama_with_drift(test_database):
    raw_model_list = {
        "models": [
            {"name": "model1", "size": 1, "specialization": "general"},
            {"name": "model2", "size": 2, "specialization": "vision"},
            {"name": "model3", "size": 3, "specialization": "vision"}

        ]
    }

    for model in raw_model_list["models"]:
        LLM_MODEL.get_or_create(
            model=model["name"],
            specialization=model["specialization"],
            size=model["size"],
            currently_available=True,
        )

    # add models
    raw_model_list["models"].pop()

    stored_llm_models = LLM_MODEL.select()

    align_db_and_ollama(raw_model_list, stored_llm_models)

    stored_llm_models = LLM_MODEL.select()
    assert stored_llm_models[0].currently_available == True
    assert stored_llm_models[1].currently_available == True
    assert stored_llm_models[2].currently_available == False

def test_align_db_and_ollama_no_drift(test_database):
    raw_model_list = {
        "models": [
            {"name": "model1", "size": 1, "specialization": "general"},
            {"name": "model2", "size": 2, "specialization": "vision"},
            {"name": "model3", "size": 3, "specialization": "vision"}

        ]
    }

    for model in raw_model_list["models"]:
        LLM_MODEL.get_or_create(
            model=model["name"],
            specialization=model["specialization"],
            size=model["size"],
            currently_available=True,
        )

    # add models
    stored_llm_models = LLM_MODEL.select()

    align_db_and_ollama(raw_model_list, stored_llm_models)

    stored_llm_models = LLM_MODEL.select()
    assert stored_llm_models[0].currently_available == True
    assert stored_llm_models[1].currently_available == True
    assert stored_llm_models[2].currently_available == True