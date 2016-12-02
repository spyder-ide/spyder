"""
This module contains the Manager API.

"""
import weakref


class Manager(object):
    """
    A manager manages a specific aspect of a CodeEdit instance:
        - backend management (start/stop server, request work,...)
        - modes management
        - panels management and drawing
        - file manager

    Managers are typically created internally when you create a CodeEdit.
    You interact with them later, e.g. when you want to start the backend
    process or when you want to install/retrieve a mode or a panel.

    ::
        editor = CodeEdit()

        # use the backend manager to start the backend server
        editor.backend.start(...)
        editor.backend.send_request(...)

        # use the panels controller to install a panel
        editor.panels.install(MyPanel(), MyPanel.Position.Right)
        my_panel = editor.panels.get(MyPanel)

        # and so on

    """

    @property
    def editor(self):
        """
        Return a reference to the parent code edit widget.
        """
        return self._editor()

    def __init__(self, editor):
        """
        :param editor: CodeEdit instance to control
        """
        self._editor = weakref.ref(editor)
