# prompts
DO_NOT_MAKEUP =  "If you do not know the answer, do not make one up. Instead let me know that you do not know that information"
ACURATE_RESPONSE = "The previous response was accurate."
EVALUATION_QUESTION = "Evaluate the previous answer for accuracy and revise the if necessary. If the previous answer largely correct and you do have not substantive revisions, please respond with: " + ACURATE_RESPONSE + " " + DO_NOT_MAKEUP

#list added in  topics_coontexts
ADD_TOPIC_TO_CHAT = f"Create a concise topic description about the current conversation. \
            Use as few words as possible, ideally 2 or 3 words. \
            This should be concise like a bullet point in presentiation, but should contain no symbols. \
            If this is about code, include the language, framework that is discussed, or both. \
            Only crete a new topic summary if there is not an obvious match with a previous summary here: " 

# creaate a category
EXISTING_CATEGORY_TO_CHAT = "Can the topic summary be logically filed under an existing category from this list of categories? "
CREATE_NEW_CATEGORY = "If it can, output the name of appropiate category. If it cannot not. Create a concise category name of no more than 2 words generally describing the summary." \
"If this is a programming langage only return the language name."
# contexts 
EVALUTATE_CONTEXT = "You are a helpful professional, evaluating for accuracy and editing a response if necessary."

