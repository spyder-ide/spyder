"""
Tests for the IPython console.
"""

def test_new_ipython_console():
    """Test the ability to open a new IPython console."""
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    from spyderlib.plugins.ipythonconsole import IPythonConsole
    from spyderlib.spyder import MainWindow
    mw = MainWindow()
    i = IPythonConsole(mw)
    i.register_plugin()
    i = IPKernelApp()
