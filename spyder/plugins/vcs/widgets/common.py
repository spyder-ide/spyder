#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common stuff for VCS UI components."""

# Standard library imports
from typing import Union, Optional, Sequence
from functools import partial
from contextlib import contextmanager

# Third party imports
from qtpy.QtCore import Slot, QTimer, Signal

# Local imports
from .utils import SLOT, ThreadWrapper
from ..backend.api import VCSBackendManager
from ..backend.errors import VCSError

# Singleton
NO_VALUE = type("NO_VALUE", (), {})()


class BaseComponent(object):
    """
    The base of all components.

    It cannot be instanced direcly. Always subclass it
    with a QObject subclass (e.g. QWidget) in the bases list
    to allows signals and the refresh timer.

    Warnings
    --------
    Due to Qt/C++ inhiterance, when subclassing
    always put first this class, then the desired subclass of QObject.
    If you don't do that, an unexpected TypeError will be raised.
    """

    # Signal definitions
    sig_vcs_error = Signal(VCSError)
    """
    This signal is emitted when VCSError is raised.

    Parameters
    ----------
    ex : VCSError
        The raised exception.
    """

    # TODO: Add it to config
    REFRESH_TIME: Optional[int] = None
    """
    The interval (in ms) when an automatic refresh is done.

    If it is None or the refresh method is not implemented,
    automatic refresh is disabled.
    """
    def __init__(self, manager: VCSBackendManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager

        if (self.REFRESH_TIME is not None
                and self.refresh != BaseComponent.refresh):
            self.timer = QTimer(self)
            self.timer.setInterval(self.REFRESH_TIME)
            self.timer.timeout.connect(self.refresh)
            self.timer.start()
        else:
            self.timer = None

    # Optional methods
    @Slot()
    def setup(self) -> None:
        """
        Setup the component when the repository changes.

        This method may be called many times.
        """

    @Slot()
    def refresh(self) -> None:
        """
        Do a component refresh by querying the backend.
        """

    # Utilities
    def do_call(self,
                feature_name: Union[str, Sequence[str]],
                *args,
                result_slots: Sequence[SLOT] = (),
                **kwargs) -> Optional[ThreadWrapper]:
        """
        Call a backend method.

        Parameters
        ----------
        feature_name : str, or tuple of str
            The feature name to get and call.
            Has te same meaning of :meth:`~VCSBackendManager.safe_check`
            feature_name parameter.

        result_slots : Sequence[SLOT], optional
            The slots to call when the call is done successfully.
            Will be passed to :class:`~ThreadWrapper` constructor.

        Returns
        -------
        ThreadWrapper
            The thread instance.
        """
        if not isinstance(result_slots, Sequence):
            result_slots = (result_slots, )

        feature = self.manager.safe_check(feature_name)
        if feature:
            thread = ThreadWrapper(
                self,
                partial(feature, *args, **kwargs),
                result_slots=result_slots,
                error_slots=(partial(self.error_handler, raise_=True), ),
            )
            thread.start()
            return thread
        return None

    @Slot(Exception)
    def error_handler(self, ex: Exception, raise_: bool = False) -> bool:
        """
        An utility method to handle backend exceptions.

        It checks if the given exception is an instance of :class:`~VCSError`.

        Parameters
        ----------
        ex : Exception
            The exception to filter.
        raise_ : bool, optional
            If True and the exception is not an instance of
            :class:`~VCSError`, then that exception will be raised.
            The default is False.

        Raises
        ------
        Exception
            If raise_ is True and the exception is not an instance of
            :class:`~VCSError`.

        Returns
        -------
        bool
            If raise_ is False, returns True if the error is an instance of
            :class:`~VCSError`, False otherwise.
            It is the same of `isinstance(ex, VCSError)`.
        """
        if isinstance(ex, VCSError):
            self.sig_vcs_error.emit(ex)
            return True
        if raise_:
            raise ex
        return False

    @contextmanager
    def block_timer(self) -> None:
        """
        A context utility to temporary block automatic refreshing.
        """
        if self.timer is not None:
            self.timer.stop()
        yield
        if self.timer is not None:
            self.timer.start()
