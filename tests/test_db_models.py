from src.myllamacli.db_models import Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings



def test_Context_creation(test_database):
    context = Context.create(text="test context")
    result = Context.get_by_id(1)
    assert result.text == "test context"