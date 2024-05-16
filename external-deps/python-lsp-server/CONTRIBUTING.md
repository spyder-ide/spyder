# Setup the environment

1. Clone the repo: `git clone git@github.com:python-lsp/python-lsp-server.git`
2. Create the virtual environment: `python -m venv .venv`
3. Activate: `source .venv/bin/activate`
4. Install an editable installation: `pip install -e .`
    - This will ensure you'll see your edits immediately without reinstalling the project
5. Configure your editor to point the pylsp executable to the one in `.venv`

## Trying out if it works

Go to file `pylsp/python_lsp.py`, function `start_io_lang_server`,
and on the first line of the function, add some logging:

```py
log.info("It works!")
```

Save the file, restart the LSP server and you should see the log line:

```
2023-10-12 16:46:38,320 CEST - INFO - pylsp._utils - It works!
```

Now the project is setup in a way you can quickly iterate change you want to add.

# Running tests

1. Install runtime dependencies: `pip install .[all]`
2. Install test dependencies: `pip install .[test]`
3. Run `pytest`: `pytest -v`

## Useful pytest options

- To run a specific test file, use `pytest test/test_utils.py`
- To run a specific test function within a test file,
  use `pytest test/test_utils.py::test_debounce`
- To run tests matching a certain expression, use `pytest -k format`
- To increase verbosity of pytest, use `pytest -v` or `pytest -vv`
- To enter a debugger on failed tests, use `pytest --pdb`
