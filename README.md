# myllamatui
A simple terminal ui to interact with a local llm and store your chat history. This is intended to be used locally by a single user. 

This is very much a work in progress.

Running Prereq: 
1. Install Ollama or pull down the containerized version. I prefer this method. I believe that the docker native version for running llamas should work also.

To start your container use= something like:
$docker run -d -v ollama_data:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
**Note you really want persisteant data here. You can change the port, but you'll want to do in the ollamatui also.


TUI installation:
<br>
Create a python venv

Install deps 

If not installed as a package you will want to add the python path:  
```export PYTHONPATH="${PYTHONPATH}:${PWD}"```
and then kick off with 
```python src/mullamatui/app.py```

Using the TUI:
The app should pop up. If don't have any models pulled down in Ollama, you can you use setttings - > Edit Models to manage pulling and deleting models.