# prompts
DO_NOT_MAKEUP = "If you do not know the answer, do not make one up. Instead let me know that you do not know that information"
ACURATE_RESPONSE = "The previous response was accurate."
EVALUATION_QUESTION = (
    "Evaluate the previous answer for accuracy and revise the if necessary. If the previous answer largely correct and you do have not substantive revisions, please respond with: "
    + ACURATE_RESPONSE
    + " "
    + DO_NOT_MAKEUP
)

# list added in  topics_coontexts
ADD_OR_APPLY_TOPIC_TO_CHAT = f"Create a concise topic description about the current conversation. \
            Use as few words as possible, ideally 2 or 3 words. \
            This should be concise like a bullet point in presentiation. Do not include any symobls. \
            If this is about code, include the framework that is discussed. If the similarity between the summary you created."


ASSESS_SUMMARY_1 = "If the similarity between the summary here: "
# apply to both Topic and Cetegory
ASSESS_SUMMARY_2 = "and one of the items in the list here: "
ASSESS_SUMMARY_3 = "is 50% or higher, output only the item in the list, otherwise output the summary you just created."

# creaate a category
CREATE_NEW_CATEGORY = "Create a new generalized category of no more than 2 words describing the topic. If this is a programming langage only return the language name. \
    This should be concise like a bullet point in presentiation. Do not include any symobls."
CATEGORY_ASSESS = "is 25% or higher, output only the item in the list, otherwise output the summary you just created."
# contexts
EVALUTATE_CONTEXT = "You are a helpful professional, evaluating for accuracy and editing a response if necessary."
