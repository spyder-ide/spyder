# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder default text snippets.

Notes:

1. Please preserve the structure of this dictionary. This is what
   we need to send to the snippet plugin to configure it.
2. All snippets added here need to comply with the LSP snippet grammar:
   https://microsoft.github.io/language-server-protocol/specifications/specification-current/#snippet_syntax
3. The snippets are grouped according to the text that triggers it and each
   snippet has the option to delete the trigger text if necessary.
4. Right now, the snippets are restricted to the languages supported by the LSP
   (hard-coded), this will change on future releases of Spyder.
"""

from textwrap import dedent


PYTHON_SNIPPETS = {
    'class': {
        'plain': {
            'text': dedent("""
                class ${1:ClassName}:
                    def __init__(self, ${2:*args}, ${3:**kwargs}):
                        ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'inheritance': {
            'text': dedent("""
                class ${1:ClassName}($2):
                    def __init__(self, ${3:*args}, ${4:**kwargs}):
                        super().__init__(${5:*args}, ${6:**kwargs})$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'def': {
        'method': {
            'text': dedent("""
                def ${1:method_name}(self, ${2:*args}, ${3:**kwargs}):
                    ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'function': {
            'text': dedent("""
                def ${1:func_name}(${2:*args}, ${3:**kwargs}):
                    ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'for': {
        'range': {
            'text': dedent("""
                for ${1:i} in range(${2:0}, ${3:n}):
                    ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'iterator': {
            'text': dedent("""
                for ${1:x} in ${2:iterator}:
                    ${3:pass}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'while': {
        'condition': {
            'text': dedent("""
                while ${1:cond}:
                    ${2:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'infinite': {
            'text': dedent("""
                while True:
                    ${1:pass}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'import': {
        'package': {
            'text': dedent("""
                import ${1:package}$0
            """).strip(),
            'remove_trigger': False
        },
        'alias': {
            'text': dedent("""
                import ${1:package} as ${2:alias}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'from': {
        'import': {
            'text': dedent("""
                from ${1:package} import ${2:module}$0
            """).strip(),
            'remove_trigger': False
        },
        'alias': {
            'text': dedent("""
                from ${1:package} import ${2:module} as ${3:alias}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'async': {
        'def': {
            'text': dedent("""
                async def ${1:func_name}(${2:*args}, ${3:**kwargs}):
                    ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'method': {
            'text': dedent("""
                async def ${1:method_name}(self, ${2:*args}, ${3:**kwargs}):
                    ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'for': {
            'text': dedent("""
                async for ${1:x} in ${2:iterator}:
                    ${3:pass}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'try': {
        'except': {
            'text': dedent("""
                try:
                    ${1:pass}
                except ${2:Exception}:
                    ${3:pass}$0
            """),
            'remove_trigger': False
        },
        'except alias': {
            'text': dedent("""
                try:
                    ${1:pass}
                except ${2:Exception} as ${3:e}:
                    ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'except/finally': {
            'text': dedent("""
                try:
                    ${1:pass}
                except ${2:Exception}:
                    ${3:pass}
                finally:
                    ${4:pass}$0
            """).strip(),
            'remove_trigger': False
        },
        'except alias/finally': {
            'text': dedent("""
                try:
                    ${1:pass}
                except ${2:Exception} as ${3:e}:
                    ${4:pass}
                finally:
                    ${5:pass}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'with': {
        'context': {
            'text': dedent("""
                with ${1:context} as ${2:alias}:
                    ${3:pass}$0
            """).strip(),
            'remove_trigger': False
        }
    },
    'list': {
        'comprehension': {
            'text': dedent("""
                [${1:x} for ${2:x} in ${3:iterator}]$0
            """).strip(),
            'remove_trigger': True
        },
        'comprehension if': {
            'text': dedent("""
                [${1:x} for ${2:x} in ${3:iterator} if ${4:cond}]$0
            """).strip(),
            'remove_trigger': True
        },
        'comprehension if/else': {
            'text': dedent("""
                [${1:x} if ${2:cond} else ${3:other} for ${4:x} in ${5:iterator}]$0
            """).strip(),
            'remove_trigger': True
        }
    },
    'dict': {
        'comprehension': {
            'text': dedent(r"""
                {${1:key}:${2:value} for ${3:elem} in ${4:iterator}\}$0
            """).strip(),
            'remove_trigger': True
        },
        'comprehension if': {
            'text': dedent(r"""
                {${1:key}:${2:value} for ${3:elem} in ${4:iterator} if ${5:cond}\}$0
            """).strip(),
            'remove_trigger': True
        }
    },
    'set': {
        'comprehension': {
            'text': dedent(r"""
                {${1:elem} for ${2:elem} in ${3:iterator}\}$0
            """).strip(),
            'remove_trigger': True
        },
        'comprehension if': {
            'text': dedent(r"""
                {${1:elem} for ${2:elem} in ${3:iterator} if ${4:cond}\}$0
            """).strip(),
            'remove_trigger': True
        },
        'comprehension if/else': {
            'text': dedent(r"""
                {${1:elem} if ${2:cond} else ${3:other} for ${4:elem} in ${5:iterator}\}$0
            """).strip(),
            'remove_trigger': True
        }
    }
}

SNIPPETS = {
    'python': PYTHON_SNIPPETS
}
