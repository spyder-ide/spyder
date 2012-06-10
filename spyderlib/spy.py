"""
Spyder's structures accessible at run time from internal console
("Spyder's DNA").

>>> dir()
['__builtins__', 'execfile', 'help', 'raw_input', 'runfile', 'spy']
>>> dir(spy)
['__builtins__', 'app', 'window']
>>>  spy.window.console.get_plugin_title()
u'Internal console'

Inspired by:
  http://wiki.blender.org/index.php/Doc:2.6/Manual/Extensions/Python/Console

"""

# Cleanup useless variables from module namespace
del __doc__
del __file__
del __name__
del __package__

# Variables accessible at run time
app = None
window = None
