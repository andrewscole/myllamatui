import logging

from myllamacli.db_models import Context, Topic, LLM_MODEL


# helper defs to populate select boxes
def model_choice_setup():
    all_models = LLM_MODEL.select()
    model_select = iter(
        (str(model.model), str(model.id))
        for model in all_models
        if model.currently_available == True
    )
    return model_select


def context_choice_setup():
    contexts = Context.select()
    context_select = iter((str(context.text), str(context.id)) for context in contexts)
    return context_select


def create_topics_select():
    topics = Topic.select()
    topic_select = iter((str(topic.text), str(topic.id)) for topic in topics if topic.text != "default") 
    return topic_select