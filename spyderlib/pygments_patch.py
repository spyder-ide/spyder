# -*- coding: utf-8 -*-
#
# Copyright © 2014 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Patching pygments to avoid errors with IPython console
"""

def apply():
    """
    Monkey patching pygments
    See Issue 2042 and https://github.com/ipython/ipython/pull/6878
    """
    from spyderlib.utils.programs import is_module_installed
    if is_module_installed('pygments', '<2.0') and \
      is_module_installed('IPython', '>3.0'):
          return
    
    # Patching IPython's patch of RegLexer (Oh God!!)
    from pygments.lexer import _TokenType, Text, Error
    from spyderlib.py3compat import to_text_string
    try:
        from IPython.qt.console.pygments_highlighter import RegexLexer
    except ImportError:
        from IPython.frontend.qt.console.pygments_highlighter import RegexLexer
    def get_tokens_unprocessed(self, text, stack=('root',)):
        pos = 0
        tokendefs = self._tokens
        if hasattr(self, '_saved_state_stack'):
            statestack = list(self._saved_state_stack)
        else:
            statestack = list(stack)
        statetokens = tokendefs[statestack[-1]]
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)
                if m:
                    if action is not None:
                        if type(action) is _TokenType:
                            yield pos, action, m.group()
                        else:
                            for item in action(self, m):
                                yield item
                    pos = m.end()
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    statestack.pop()
                                elif state == '#push':
                                    statestack.append(statestack[-1])
                                else:
                                    statestack.append(state)
                        elif isinstance(new_state, int):
                            # pop
                            del statestack[new_state:]
                        elif new_state == '#push':
                            statestack.append(statestack[-1])
                        else:
                            assert False, "wrong state def: %r" % new_state
                        statetokens = tokendefs[statestack[-1]]
                    break
            else:
                try:
                    if text[pos] == '\n':
                        # at EOL, reset state to "root"
                        pos += 1
                        statestack = ['root']
                        statetokens = tokendefs['root']
                        yield pos, Text, to_text_string('\n')
                        continue
                    yield pos, Error, text[pos]
                    pos += 1
                except IndexError:
                    break
        self._saved_state_stack = list(statestack)

    RegexLexer.get_tokens_unprocessed = get_tokens_unprocessed
