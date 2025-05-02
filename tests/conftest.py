import pytest
from peewee import SqliteDatabase

from myllamacli.db_models import BaseModel, Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings

# List all models you want to test
TEST_MODELS = [Context, Topic, Category, LLM_MODEL, Chat, CLI_Settings]

# Create an in-memory SQLite database
test_db = SqliteDatabase(':memory:')

@pytest.fixture(scope="function")
def test_database():
    # Temporarily rebind the models to the test DB
    test_db.bind(TEST_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(TEST_MODELS)

    # Swap out the original database on the base model
    original_database = BaseModel._meta.database
    BaseModel._meta.database = test_db

    yield  # Run the test

    test_db.drop_tables(TEST_MODELS)
    test_db.close()
    BaseModel._meta.database = original_database
