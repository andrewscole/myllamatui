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
    print(result.id)
    assert result.text == "test topic"
    # this is kind of stupid and probably not a great test
    assert str(result.category_id) == str(cat_id)

def test_LLM_MODEL_creation(test_database):
    context = LLM_MODEL.create(model="MyFakeModel", size=34567, specialization="general", currently_available=True)
    result = LLM_MODEL.get_by_id(1)
    assert result.model == "MyFakeModel"
    assert result.size == 34567
    assert result.specialization == "general"
    assert result.currently_available == True