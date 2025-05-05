import pytest

from src.myllamacli.db_models import Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings



def test_Context_creation(test_database):
    Context.create(text="test context")
    result = Context.get_by_id(1)
    assert result.text == "test context"

def test_Category_creation(test_database):
    Category.create(text="test category")
    result = Category.get_by_id(1)
    assert result.text == "test category"


def test_Topic_creation(test_database):
    category_test = Category.create(text="test category")
    Topic.create(text="test topic", category_id=category_test.id)
    cat_id = category_test.id
    result = Topic.get_by_id(1)
    assert result.text == "test topic"
    # this is kind of stupid and probably not a great test
    assert str(result.category_id) == str(cat_id)

def test_LLM_MODEL_creation(test_database):
    result = LLM_MODEL.create(model="MyFakeModel", size=34567, specialization="general", currently_available=True)
    assert result.model == "MyFakeModel"
    assert result.size == 34567
    assert result.specialization == "general"
    assert result.currently_available == True


def test_chat_creation(test_database):
    test_model = LLM_MODEL.create(model="FakeModel", size=34567, specialization="general", currently_available=True)
    test_context = Context.create(text="my test context")
    test_category = Category.create(text="my test category")
    test_topic = Topic.create(text="test topic", category_id=test_category.id)
    test_question = "What is the meaning of Life?"
    test_answer = "42"
    result = Chat.create(question=test_question, answer=test_answer, context_id=test_context.id, topic_id=test_topic.id, llm_model_id=test_model.id)

    assert result.question == "What is the meaning of Life?"
    assert result.answer == "42"
    assert str(result.topic_id) == str(test_topic.id)
    assert str(result.context_id) == str(test_context.id)
    assert str(result.llm_model_id) == str(test_model.id)


def update_chat_topic_from_summary(test_database):
    test_model = LLM_MODEL.create(model="FakeModel", size=34567, specialization="general", currently_available=True)
    test_context = Context.create(text="my test context")
    test_category = Category.create(text="my test category")
    test_topic = Topic.create(text="test topic", category_id=test_category.id)
    test_question = "What is the meaning of Life?"
    test_answer = "42"
    result = Chat.create(question=test_question, answer=test_answer, context_id=test_context.id, topic_id=test_topic.id, llm_model_id=test_model.id)

    assert str(result.topic_id) == istrnt(test_topic.id)

    new_test_topic = Topic.create(text="new test topic", category_id=test_category.id)
    result.update_chat_topic_from_summary(new_test_topic.id)
    
    assert str(result.topic_id) == str(new_test_topic.id)






def test_cli_settings_creation(test_database):
    test_model = LLM_MODEL.create(model="FakeModel", size=34567, specialization="general", currently_available=True)
    test_context = Context.create(text="my test context")
    test_category = Category.create(text="my test category")
    test_topic = Topic.create(text="test topic", category_id=test_category.id)
    result = CLI_Settings.create(url="http://fakeurl", llm_model_id=test_model.id, context_id=test_context.id, topic_id=test_topic.id)

    assert result.url == "http://fakeurl"
    assert str(result.topic_id) == str(test_topic.id)
    assert str(result.context_id) == str(test_context.id)
    assert str(result.llm_model_id) == str(test_model.id)