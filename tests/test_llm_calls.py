import pytest
import httpx
from unittest.mock import patch, AsyncMock

from src.myllamacli.llm_calls import (
    generate_endpoint,
    generate_data_for_chat,
    generate_data_for_model_pull,
    generate_input_dict,
    parse_response,
    post_to_llm,
    get_from_llm,
    delete_llm_call,
)

# Mocking httpx responses
class MockResponse:
    def __init__(self, status_code, json):
        self.status_code = status_code
        self.json_result = json

    async def json(self):
        return self.json_result


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_post_to_llm(mock_post):
    # Arrange
    mock_post.return_value = httpx.Response(status_code=200, json={"message": "Success"})

    api_endpoint = "https://example.com/api/post"
    data = {"key": "value"}

    # Act
    response = await post_to_llm(api_endpoint, data)

    # Assert
    mock_post.assert_called_once_with(api_endpoint, json=data, timeout=900.0)
    assert response.status_code == 200
    assert response.json() == {"message": "Success"}


@pytest.mark.asyncio
@patch("src.myllamacli.llm_calls.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_get_from_llm(mock_get):
    # Arrange
    mock_get.return_value = httpx.Response(status_code=200, json={"data": "test_data"})

    api_endpoint = "https://example.com/api/get"

    # Act
    response = await get_from_llm(api_endpoint)

    # Assert
    mock_get.assert_called_once_with(api_endpoint, timeout=300.0)
    assert response.status_code == 200
    assert response.json() == {"data": "test_data"}


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_delete_llm_call(mock_request):
    # Arrange
    mock_request.return_value = httpx.Response(status_code=200, json={"deleted": True})

    api_endpoint = "https://example.com/api/delete"
    data = {"id": 123}

    # Act
    response = await delete_llm_call(api_endpoint, data)

    # Assert
    mock_request.assert_called_once_with(
        method="DELETE", url=api_endpoint, json=data, timeout=300.0
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}


def test_generate_endpoint():
    url = "http://example.com"
    action = "show_list"
    endpoint = generate_endpoint(url, action)
    assert endpoint == "http://example.com/api/tags"

def test_generate_data_for_chat():
    MESSAGES = [{"role": "user", "content": "Hello"}]
    model = "gpt-3.5-turbo"
    data = generate_data_for_chat(MESSAGES, model)
    assert data == {
        "model": "gpt-3.5-turbo",
        "stream": False,
        "messages": [{"role": "user", "content": "Hello"}],
    }

def test_generate_data_for_model_pull():
    model = "gpt-3.5-turbo"
    data = generate_data_for_model_pull(model)
    assert data == {"model": "gpt-3.5-turbo"}

def test_generate_input_dict():
    input_text = "Hello, world!"
    data = generate_input_dict(input_text)
    assert data == {"role": "user", "content": "Hello, world!"}

def test_parse_response_message():
    response_json = {
        "message": {
            "content": "This is a message"
        }
    }
    key, answer = parse_response(response_json)
    assert key == "message"
    assert answer == "This is a message"

def test_parse_response_response():
    response_json = {
        "response": "This is a response"
    }
    key, answer = parse_response(response_json)
    assert key == "response"
    assert answer == "This is a response"
