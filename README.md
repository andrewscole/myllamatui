# myllamacli
A simple terminal ui  to interact with a local llm and store your chat history locally with no calls to the outside world (unless you want to add them)

This is very much in progress.

Running:
Prereq:
Install Ollama or pull down the containerized version. I prefer this method. I believe that the docker native version for running llamas should work also.

Start your container with something like: 
$docker run -d -v ollama_data:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
Note you really want persisteant data here. You can change the port, but you'll want to do in the ollamatui also.

myllamatui:
Create a python venv, Install deps and run.
