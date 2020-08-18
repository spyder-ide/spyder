#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Builtin backends for Git and Mercurial."""

# Standard library imports
import ast
import platform
import os
import os.path as osp
import re
import subprocess

# Third party imports
import pexpect

# Local imports
from spyder.utils import programs
from spyder.utils.vcs import (get_git_refs, is_hg_installed, get_hg_revision)

from .api import VCSBackendBase, ChangedStatus, checker
from .errors import (VCSAuthError, VCSPropertyError, VCSBackendFail,
                     VCSUnexpectedError)
from .mixins import CredentialsKeyringMixin

__all__ = ("GitBackend", "MercurialBackend")


class GitBackend(
        # Git for Windows uses its own credentials manager
        CredentialsKeyringMixin if platform.system() != "Windows" else object,
        VCSBackendBase):
    """An implementation of VCSBackendBase for Git."""

    VCSNAME = "git"

    FEATURES = {
        "file-state": True,
        "file-diff": False,
        "current-branch": True,
        "change-branch": True,
        "branches": True,
        "manage-branches": False,
        "stage-unstage": True,
        "commit": True,
        "pull": True,
        "push": True,
        "undo": False,
        "history": False,
        "merge": False,
    }

    # credentials implementation
    REQUIRED_CREDENTIALS = ("username", "password")
    SCOPENAME = "spyder-vcs-git"

    def __init__(self, *args):
        super().__init__(*args)
        if not is_git_installed():
            raise VCSBackendFail(self.repodir, type(self), programs=("git", ))

        repodir = self.repodir
        self.repodir = get_git_root(self.repodir)
        if not self.repodir:
            # use the original dir
            raise VCSBackendFail(repodir,
                                 type(self),
                                 is_valid_repository=False)

        username = get_git_username(self.repodir)
        if username:
            try:
                self.get_user_credentials(username=username)
            except VCSAuthError:
                # No saved credentials found
                pass

    # CredentialsKeyringMixin implementation
    @property
    def credential_context(self):
        remote = git_get_remote(self.repodir)
        if remote:
            return remote
        raise ValueError("Failed to get git remote")

    # VCSBackendBase implementation
    @property
    @checker("current-branch")
    def branch(self) -> str:
        revision = get_git_status(self.repodir)
        if revision and revision[0][0]:
            return revision[0][0]
        raise VCSPropertyError("branch", "get")

    @branch.setter
    @checker("change-branch")
    def branch(self, branchname: str):
        # Checks:
        # - if the "branches" feature is available and given branch exists,
        #   without "branches" feature this check is skipped
        # - check change_git_branch result
        # - check if branch is really changed
        if not ((not self.check_features("branches", suppress_raise=True)
                 or branchname in self.branches) and change_git_branch(
                     self.repodir, branchname) and self.branch != branchname):

            raise VCSPropertyError("branch", "set")

    @property
    @checker("branches")
    def branches(self) -> list:
        branches = get_git_refs(self.repodir)[0]
        if branches:
            return branches
        raise VCSPropertyError("branches", "get")

    @property
    # @checker("branches")
    def editable_branches(self) -> list:
        return [x for x in self.branches if not x.startswith("remotes/")]

    @property
    @checker("file-state")
    def changes(self) -> list:
        filestates = get_git_status(self.repodir)[2]
        if filestates is None:
            raise VCSPropertyError(
                "changes",
                "get",
                error_message="Failed to get git changes",
            )
        changes = []
        for record in filestates:
            if len(record) == 3:
                path, staged, unstaged = record
                staged, unstaged = (ChangedStatus.from_string(staged),
                                    ChangedStatus.from_string(unstaged))
                # remove git quote from file
                if len(path) > 3 and path[0] == path[-1] in ("'", '"'):
                    path = path[1:-1]

                unescaped_path = path
                path = []

                # As stated here:
                # https://docs.python.org/3/library/ast.html#ast.literal_eval
                # ast.literal_eval can crash the interpreter
                # if the given input is too big,
                # therefore the path is break down into chunks.
                try:
                    for i in range(0, len(unescaped_path), 16384):
                        path.append(
                            ast.literal_eval("'" +
                                             unescaped_path[i:i + 16384] +
                                             "'"))
                except (ValueError, SyntaxError):
                    # ???: may this error should be raised
                    continue
                else:
                    path = "".join(path)

                if unstaged != ChangedStatus.UNCHANGED:
                    changes.append(dict(path=path, kind=unstaged,
                                        staged=False))
                if staged != ChangedStatus.UNCHANGED:
                    changes.append(dict(path=path, kind=staged, staged=True))
        return changes

    @checker("stage-unstage")
    def stage(self, path: str) -> bool:
        status = git_stage_file(self.repodir, path)
        if isinstance(status, bool):
            return status
        raise VCSUnexpectedError(
            method="stage",
            error_message="Failed to stage file {}".format(path),
        )

    @checker("stage-unstage")
    def unstage(self, path: str) -> bool:
        status = git_unstage_file(self.repodir, path)
        if isinstance(status, bool):
            return status

        raise VCSUnexpectedError(
            method="unstage",
            error_message="Failed to unstage file {}".format(path),
        )

    @checker("commit")
    def commit(self, message: str, is_path: bool = None):
        if is_path is None:
            # Check if message is a valid path
            is_path = osp.isfile(message)

        status = None
        if is_path:
            status = git_commit_file_message(self.repodir, message)
        else:
            status = git_commit_message(self.repodir, message)
        if isinstance(status, bool):
            return status

        raise VCSUnexpectedError(
            method="commit",
            error_message="Failed to commit",
        )

    @checker("pull")
    def fetch(self, sync: bool = False) -> (int, int):
        if sync:
            self._remote_operation("fetch")
        return get_git_status(self.repodir)[1]

    @checker("pull")
    def pull(self) -> bool:
        return self._remote_operation("pull")

    @checker("push")
    def push(self) -> bool:
        return self._remote_operation("push")

    def _remote_operation(self, operation: str, *args):
        """Helper for remote operations."""
        if platform.system() == "Windows":
            # Windows uses its own credentials manager by default
            status = git_remote_operation_windows(self.repodir, operation,
                                                  *args)
            if isinstance(status, bool):
                return status
        else:
            credentials = self.credentials
            username = (credentials.get("username", "")
                        or get_git_username(self.repodir) or "")
            status = git_remote_operation_posix(
                self.repodir,
                operation,
                username,
                credentials.get("password", ""),
                *args,
            )
            if status is True:
                # auth success

                # Check if current git username is changed
                # compared to the credentials username.
                cred_username = credentials.get("username", "")
                if cred_username and not credentials.get("password", ""):
                    username = get_git_username(self.repodir)
                    if username != cred_username:
                        set_git_username(self.repodir, cred_username)
                return True

            if status is False:
                # Auth failed
                raise VCSAuthError(
                    username=username,
                    password=credentials.get("password"),
                    error_message="Wrong credentials",
                )

        raise VCSUnexpectedError(
            method=operation,
            error_message="Failed to {} from remote".format(operation),
        )


class MercurialBackend(VCSBackendBase):  # pylint: disable=W0223
    """An implementation of VCSBackendBase for mercurial (hg)."""

    VCSNAME = "mercurial"
    FEATURES = {
        "file-state": False,
        "file-diff": False,
        "current-branch": True,
        "change-branch": False,
        "branches": False,
        "manage-branches": False,
        "stage-unstage": False,
        "commit": False,
        "pull": False,
        "push": False,
        "undo": False,
        "history": False,
        "merge": False,
    }

    def __init__(self, *args):
        super().__init__(*args)
        if not is_hg_installed():
            raise VCSBackendFail(self.repodir, type(self), programs=("hg", ))

    @property
    @checker("current-branch")
    def branch(self) -> str:
        revision = get_hg_revision(self.repodir)
        if revision:
            return revision[2]
        raise VCSPropertyError("branch", "get")


# --- VCS operation functions ---

_GIT_STATUS_MAP = {
    " ": "UNCHANGED",
    "A": "ADDED",
    "D": "REMOVED",
    "M": "MODIFIED",
    "R": "REMOVED",
    "C": "COPIED",
    "??": "ADDED",
}


def is_git_installed():
    return programs.find_program('git') is not None


def get_git_root(path):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ["rev-parse", "--show-toplevel"],
                                        cwd=path)
            output, _err = proc.communicate()
            if proc.returncode == 0:
                return output.decode().rstrip(os.linesep)

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def get_git_username(repopath):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ['config', "--get", "user.name"],
                                        cwd=repopath)
            output, _err = proc.communicate()
            if proc.returncode == 0:
                return output.decode().strip("\n")

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def set_git_username(repopath, username):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(
                git,
                ['config', "--local", "user.name", username],
                cwd=repopath,
            )
            output, _err = proc.communicate()
            if proc.returncode == 0:
                return output.decode().strip("\n")
        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def get_git_unstaged_diff(filepath, repopath):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ['diff', "HEAD", filepath],
                                        cwd=repopath)
            output, _err = proc.communicate()
            if proc.returncode == 0:
                return output.decode().strip()
        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def get_git_staged_diff(filepath, repopath):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ['diff', "--staged", filepath],
                                        cwd=repopath)
            output, _err = proc.communicate()

            return output.decode().strip()
        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def change_git_branch(repopath, branchname):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ['checkout', branchname],
                                        cwd=repopath)
            return not proc.returncode

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def get_git_status(repopath, pathspec="."):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, [
                'status', "-b", "--porcelain=v1", "--ignore-submodule=all",
                pathspec
            ],
                                        cwd=repopath)
            output, _err = proc.communicate()
            if proc.returncode != 0:
                return None, None, None

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
        else:
            changes = []
            lines = output.decode().strip(" \n").splitlines()
            behind = ahead = 0
            local = remote = None
            if lines:
                # match first line
                match = re.match(
                    # local branch (group 1)
                    r"^## (.+?)"
                    # remote branch (group 2)
                    r"(?:\.\.\.(.+?))?"
                    # behind/ahead (group 3 and 4)
                    r"(?: \[(.+? \d+)(?:, )?(.+? \d+)?]"
                    # extra cases (group 5)
                    r"|(?: \((.+?)\)))?$",
                    lines[0],
                )
                if match:
                    # local remote match
                    del lines[0]
                    local = match.group(1)
                    remote = match.group(2)

                    # behind ahead match
                    for group in (match.group(3), match.group(4)):
                        if group is None:
                            pass
                        elif group.startswith("behind"):
                            behind = int(group.rsplit(" ", 1)[-1])
                        elif group.startswith("ahead"):
                            ahead = int(group.rsplit(" ", 1)[-1])

                # get branch and changes
                for line in lines:
                    if line.startswith("??"):
                        changes.append((
                            line[3:],
                            "UNCHANGED",
                            _GIT_STATUS_MAP["??"],
                        ))
                    elif "R" in line[:2] or "C" in line[:2]:
                        # FIXME: skipped unless i know how to manage it
                        pass
                    else:
                        changes.append((
                            line[3:],
                            _GIT_STATUS_MAP.get(line[0], "UNKNOWN"),
                            _GIT_STATUS_MAP.get(line[1], "UNKNOWN"),
                        ))

                return (local, remote), (behind, ahead), changes

    return None, None, None


def git_stage_file(repopath, filepath):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ['add', filepath], cwd=repopath)
            proc.communicate()
            return proc.returncode == 0
        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def git_unstage_file(repopath, filepath):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ['reset', '--', filepath],
                                        cwd=repopath)
            proc.communicate()
            return proc.returncode == 0
        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def git_commit_message(repopath, message):
    git = programs.find_program('git')
    if git:
        paragraphs = []
        for paragraph in message.split("\n\n"):
            paragraphs.extend(("-m", paragraph))

        if paragraphs:
            try:
                proc = programs.run_program(git, ['commit'] + paragraphs,
                                            cwd=repopath)
                print(proc.communicate(), proc.returncode)
                return proc.returncode == 0
            except (subprocess.CalledProcessError, AttributeError, OSError):
                pass
    return None


def git_commit_file_message(repopath, path):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(git, ['commit', '-F', path],
                                        cwd=repopath)
            return proc.returncode == 0
        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def git_remote_operation_windows(repopath, command_name):
    # Windows has it's own credentials manager
    # so it's an user problem
    git = programs.find_program('git')
    if git and command_name in ("fetch", "pull", "push"):
        try:
            env = os.environ.copy()

            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GIT_ASKPASS"] = ""
            proc = programs.run_program(git, [command_name],
                                        cwd=repopath,
                                        env=env)
            return proc.returncode == 0
        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None


def git_remote_operation_posix(repopath, command_name, username, password):
    """
    Do a remote operation with credentials (if necessary).

    Parameters
    ----------
    repopath
        The git root.
    command_name
        The git command.
    username
        Username to give to git.
    password
        Password to give to git.

    Returns
    -------
    bool
        True if the entered credentials are correct, False otherwise.
    str
        The error message
    None
        If any error occurred
    """
    git = programs.find_program('git')
    if git:
        proc = pexpect.spawn(git, [command_name], cwd=repopath, timeout=10)
        i = proc.expect(["Username for .+:", pexpect.EOF, pexpect.TIMEOUT])
        if i == 0:
            proc.sendline(username)

        elif not proc.isalive():
            # No authentication required
            if proc.signalstatus:
                # bad fail
                return None

            if proc.exitstatus:
                # git error
                return proc.before

            return True

        i = proc.expect(["Password for .+:", pexpect.EOF, pexpect.TIMEOUT])
        if i == 0:
            proc.sendline(password)
        else:
            return None

        proc.expect([pexpect.EOF, pexpect.TIMEOUT])
        if proc.isalive():
            proc.wait()

        if not (proc.exitstatus or proc.signalstatus):
            return True

        message = proc.before
        if message.lower().find(b"http basic: access denied") != -1:
            return False

        return message

    return None


def git_get_remote(repopath):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(
                git, ["config", "--get", "remote.origin.url"], cwd=repopath)
            output, _err = proc.communicate()
            if proc.returncode == 0 and not _err:
                return output.decode()

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None
