from typing import List, Tuple
from peewee import *
from datetime import datetime

from myllamacli.shared_utils import set_database_path

MYLLAMACLI_DB = set_database_path()

SQLITE_DB = SqliteDatabase(MYLLAMACLI_DB)


class BaseModel(Model):
    """A base model that will use our Sqlite database."""

    class Meta:
        database = SQLITE_DB


class Context(BaseModel):
    text = TextField(unique=True)
    created_at = DateTimeField(default=datetime.now)


class Category(BaseModel):
    text = TextField(unique=True)
    created_at = DateTimeField(default=datetime.now)


class Topic(BaseModel):
    text = TextField(unique=True)
    category_id = ForeignKeyField(Category, backref="topics")
    created_at = DateTimeField(default=datetime.now)


class LLM_MODEL(BaseModel):
    model = CharField(unique=True)
    size = IntegerField()
    specialization = TextField()
    modified_at = DateTimeField(default=datetime.now)
    currently_available = BooleanField()


class Chat(BaseModel):
    question = TextField()
    answer = TextField()
    context_id = ForeignKeyField(Context, backref="contexts")
    topic_id = ForeignKeyField(Topic, backref="topics")
    llm_model_id = ForeignKeyField(LLM_MODEL, backref="llmmodels")
    created_at = DateTimeField(default=datetime.now)

    def update_chat_topic_from_summary(self, topic_id_int: int) -> int:
        """Update topic id for a chat"""
        self.topic_id = topic_id_int
        self.save()
        return self.topic_id


class CLI_Settings(BaseModel):
    url = CharField()
    llm_model_id = ForeignKeyField(LLM_MODEL, backref="llmmodels")
    context_id = ForeignKeyField(Context, backref="contexts")
    topic_id = ForeignKeyField(Topic, backref="topics")
    updated_at = DateTimeField(default=datetime.now)
