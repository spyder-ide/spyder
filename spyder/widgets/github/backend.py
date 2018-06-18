# -*- coding: utf-8 -*-
# Copyright © QCrash - Colin Duquesnoy
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Backend to open issues automatically on Github.

Taken from the QCrash Project:
https://github.com/ColinDuquesnoy/QCrash
"""

import logging
import sys
import webbrowser

try:
    import keyring
except Exception:
    pass

from qtpy.QtCore import Qt
from qtpy.QtWidgets import qApp, QMessageBox


from spyder.config.main import CONF
from spyder.config.base import _
from spyder.py3compat import PY2
from spyder.utils.external import github
from spyder.widgets.github.gh_login import DlgGitHubLogin


def _logger():
    return logging.getLogger(__name__)


class BaseBackend(object):
    """
    Base class for implementing a backend.

    Subclass must define ``button_text``, ``button_tooltip``and ``button_icon``
    and implement ``send_report(title, description)``.

    The report's title and body will be formatted automatically by the
    associated :attr:`formatter`.
    """
    def __init__(self, formatter, button_text, button_tooltip,
                 button_icon=None, need_review=True):
        """
        :param formatter: the associated formatter (see :meth:`set_formatter`)
        :param button_text: Text of the associated button in the report dialog
        :param button_icon: Icon of the associated button in the report dialog
        :param button_tooltip: Tooltip of the associated button in the report
            dialog
        :param need_review: True to show the review dialog before submitting.
            Some backends (such as the email backend) do not need a review
            dialog as the user can already review it before sending the final
            report
        """
        self.formatter = formatter
        self.button_text = button_text
        self.button_tooltip = button_tooltip
        self.button_icon = button_icon
        self.need_review = need_review
        self.parent_widget = None

    def set_formatter(self, formatter):
        """
        Sets the formatter associated with the backend.

        The formatter will automatically get called to format the report title
        and body before ``send_report`` is being called.
        """
        self.formatter = formatter

    def send_report(self, title, body, application_log=None):
        """
        Sends the actual bug report.

        :param title: title of the report, already formatted.
        :param body: body of the reporit, already formtatted.
        :param application_log: Content of the application log.
        Default is None.

        :returns: Whether the dialog should be closed.
        """
        raise NotImplementedError


class GithubBackend(BaseBackend):
    """
    This backend sends the crash report on a github issue tracker::

        https://github.com/gh_owner/gh_repo

    Usage::

        github_backend = spyder.widgets.github.backend.GithubBackend(
            'spyder-ide', 'spyder')
    """
    def __init__(self, gh_owner, gh_repo, formatter=None):
        """
        :param gh_owner: Name of the owner of the github repository.
        :param gh_repo: Name of the repository on github.
        """
        super(GithubBackend, self).__init__(
            formatter, "Submit on github",
            "Submit the issue on our issue tracker on github", None)
        self.gh_owner = gh_owner
        self.gh_repo = gh_repo
        self._show_msgbox = True  # False when running the test suite

    def send_report(self, title, body, application_log=None):
        _logger().debug('sending bug report on github\ntitle=%s\nbody=%s',
                        title, body)

        # Credentials
        credentials = self.get_user_credentials()
        if len(credentials) == 1:
            token = credentials
            username, password = None, None
        else:
            token = None
            username, password, remember = credentials
        if username is None and password is None and token is None:
            return False
        _logger().debug('got user credentials')

        # upload log file as a gist
        if application_log:
            url = self.upload_log_file(application_log)
            body += '\nApplication log: %s' % url
        try:
            if token:
                gh = github.GitHub(access_token=token)
            else:
                gh = github.GitHub(username=username, password=password)
            repo = gh.repos(self.gh_owner)(self.gh_repo)
            ret = repo.issues.post(title=title, body=body)
        except github.ApiError as e:
            _logger().warn('failed to send bug report on github. response=%r' %
                           e.response)
            # invalid credentials
            if e.response.code == 401:
                if self._show_msgbox:
                    QMessageBox.warning(
                        self.parent_widget, _('Invalid credentials'),
                        _('Failed to create Github issue, '
                          'invalid credentials...'))
            else:
                # other issue
                if self._show_msgbox:
                    QMessageBox.warning(
                        self.parent_widget,
                        _('Failed to create issue'),
                        _('Failed to create Github issue. Error %d') %
                        e.response.code)
            return False
        else:
            issue_nbr = ret['number']
            if self._show_msgbox:
                ret = QMessageBox.question(
                    self.parent_widget, _('Issue created on Github'),
                    _('Issue successfully created. Would you like to open the '
                      'issue in your web browser?'))
            if ret in [QMessageBox.Yes, QMessageBox.Ok]:
                webbrowser.open(
                    'https://github.com/%s/%s/issues/%d' % (
                        self.gh_owner, self.gh_repo, issue_nbr))
            return True

    def _get_credentials_from_settings(self):
        """Get the stored credentials if any."""
        remember = CONF.get('main', 'report_error/remember_me')
        username = CONF.get('main', 'report_error/username')
        if not remember:
            username = ''

        return username, remember

    def _store_credentials(self, username, password, remember=False):
        """Store credentials for future use."""
        if username and password and remember:
            CONF.set('main', 'report_error/username', username)
            try:
                keyring.set_password('github', username, password)
            except Exception:
                QMessageBox.warning(self.parent_widget,
                                    _('Failed to store password'),
                                    _('It was not possible to securely save '
                                      'your password. You will be prompted for'
                                      'your Github credentials next time you '
                                      'want to report an issue.'))
                remember = False
        CONF.set('main', 'report_error/remember_me', remember)

    def get_user_credentials(self):
        """Get user credentials with the login dialog."""
        password = None
        username, remember = self._get_credentials_from_settings()
        valid_py_os = not PY2 and not sys.plataform.startswith('linux')
        if username and remember and valid_py_os:
            # get password from keyring
            try:
                password = keyring.get_password('github', username)
            except Exception:
                # no safe keyring backend
                QMessageBox.warning(self.parent_widget,
                                    _('Failed to retrieve password'),
                                    _('It was not possible to retrieve your '
                                      'password. Please introduce it again.'))
        credentials = DlgGitHubLogin.login(self.parent_widget, username,
                                           password, remember)
        if len(credentials) == 3 and valid_py_os:
            self._store_credentials(*credentials)

        return credentials

    def upload_log_file(self, log_content):
        gh = github.GitHub()
        try:
            qApp.setOverrideCursor(Qt.WaitCursor)
            ret = gh.gists.post(
                description="SpyderIDE log", public=True,
                files={'SpyderIDE.log': {"content": log_content}})
            qApp.restoreOverrideCursor()
        except github.ApiError:
            _logger().warn('failed to upload log report as a gist')
            return '"failed to upload log file as a gist"'
        else:
            return ret['html_url']
