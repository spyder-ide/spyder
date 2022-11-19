# Autoimport for pylsp

Requirements:

1. install `python-lsp-server[rope]`
2. set `pylsp.plugins.rope_autoimport.enabled` to `true`

## Startup

Autoimport will generate an autoimport sqllite3 database in .ropefolder/autoimport.db on startup.  
This will take a few seconds but should be much quicker on future runs.

## Usage

Autoimport will provide suggestions to import names from everything in `sys.path`. You can change this by changing where pylsp is running or by setting rope's 'python_path' option.
It will suggest modules, submodules, keywords, functions, and classes.

Since autoimport inserts everything towards the end of the import group, its recommended you use the isort [plugin](https://github.com/paradoxxxzero/pyls-isort).

## Credits

- Most of the code was written by me, @bagel897
- [lyz-code](https://github.com/lyz-code/autoimport) for inspiration and some ideas
- [rope](https://github.com/python-rope/rope), especially @lieryan
- [pyright](https://github.com/Microsoft/pyright) for details on language server implementation
