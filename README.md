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
-Create and start a python venv (I used pyenv, but venv or any number of other envs could work.) 
-Install deps with:
``` pip install . ```  or if you want to hack at it ``` pip install -e . ```

For dev (linting stuff) and test you can use:
```pip install .[dev]``` or  ```pip install .[test]```

-Start (once docker is running ollama or you pulled it down and installed locally): 
``` python -m myllamatui ``` 

If not installed as a package you will want to add the python path:  
```export PYTHONPATH="${PYTHONPATH}:${PWD}"```
and then kick off with 
```python src/mullamatui/__main__.py```

Using the TUI:
1. The app should pop up. 
If don't have any models pulled down in Ollama, you can you use setttings - > Edit Models to manage pulling and deleting models.

2. Choose a context, Choose a model, ask a question, hit submit.