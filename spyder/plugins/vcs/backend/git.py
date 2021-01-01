#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Git backend module."""

import os
import re
import shutil
import os.path as osp
import platform
import subprocess
from typing import Dict, Tuple, Union, Optional, Sequence
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
# Standard library imports
from concurrent.futures.thread import ThreadPoolExecutor

# Third party imports
import pexpect

# Local imports
from spyder.utils import programs

from .api import ChangedStatus, VCSBackendBase, feature
from .errors import (
    VCSAuthError,
    VCSBackendFail,
    VCSFeatureError,
    VCSPropertyError
)
from .mixins import CredentialsKeyringMixin

__all__ = ("GitBackend", )

_git_bases = [VCSBackendBase]
if platform.system() != "Windows":
    # Git for Windows uses its own credentials manager
    _git_bases.insert(0, CredentialsKeyringMixin)


class GitBackend(*_git_bases):
    """An implementation of VCSBackendBase for Git."""

    VCSNAME = "git"

    # credentials implementation
    REQUIRED_CREDENTIALS = ("username", "password")
    SCOPENAME = "spyder-vcs-git"

    def __init__(self, *args):
        super().__init__(*args)
        git = programs.find_program("git")
        if git is None:
            raise VCSBackendFail(self.repodir, type(self), programs=("git", ))
        repodir = self.repodir
        retcode, self.repodir, _ = run_helper(git,
                                              ["rev-parse", "--show-toplevel"],
                                              cwd=repodir)
        if retcode or not self.repodir:
            # use the original dir
            raise VCSBackendFail(repodir,
                                 type(self),
                                 is_valid_repository=False)

        self.repodir = self.repodir.decode().rstrip("\n")

        if platform.system() != "Windows":
            retcode, username, _ = self._run(['config', "--get", "user.name"],
                                             git=git)
            if not retcode and username.strip():
                try:
                    self.get_user_credentials(
                        username=username.strip().decode())
                except (VCSAuthError, ValueError):
                    # No saved credentials found
                    pass

    # CredentialsKeyringMixin implementation
    @property
    def credential_context(self):
        # Use current remote as credential context
        retcode, remote, _ = self._run(
            ["config", "--get", "remote.origin.url"])
        if not retcode and remote:
            return remote.decode().strip("\n")
        raise ValueError("Failed to get git remote")

    # VCSBackendBase implementation
    @classmethod
    @feature()
    def create(cls,
               path: Union[str, Path],
               from_: str = None,
               credentials: Dict[str, object] = None) -> "VCSBackendBase":
        def _restore():
            if basepath is None:
                with ThreadPoolExecutor() as pool:
                    # Remove all the content of directory, but not the root.
                    pool.map(
                        lambda x: shutil.rmtree(osp.join(path, x)),
                        os.listdir(path),
                    )
            else:
                for parent in path.parents:
                    if parent == basepath:
                        break
                    parent.rmdir()

        def _raise(raw_err):
            _restore()
            raise VCSBackendFail(
                strpath,
                cls,
                programs=("git", ),
                raw_error=raw_err.decode(),
            )

        path = Path(path)
        if path.exists():
            if any(path.iterdir()):
                raise FileExistsError("Directory Exists: {}".format(path))
            basepath = None
        else:
            # Get the first existing parent folder.
            # This path will be used when something goes wrong.
            for parent in path.parents:
                if parent.exists():
                    basepath = parent
                    break
            else:
                basepath = Path.root
            os.makedirs(path)

        # Initialize repository
        strpath = str(path)
        git = programs.find_program("git")
        retcode, _, err = run_helper(git, ["init", "."], cwd=strpath)
        if retcode:
            _raise(err)

        inst = cls(strpath)
        if from_ is None:
            return inst

        # --- Clone a repository without git clone ---
        # Source:
        # https://ivan.bessarabov.com/blog/cloning-git-repo-withou-git-clone

        # Check if given remote is a valid URL
        parse_result = urlparse(from_)
        if not ((parse_result.scheme == "file" and parse_result.path)
                or all(parse_result[:3])):
            raise ValueError("{} is not a valid url".format(repr(from_)))

        # Add origin URL
        retcode, _, err = run_helper(
            git,
            ["remote", "add", "origin", from_],
            cwd=strpath,
        )
        if retcode:
            _raise(err)

        # Fetch remote
        try:
            inst.credentials = credentials
            inst.fetch(sync=True)
        except VCSAuthError as ex:
            _restore()
            raise ex

        # Get default branch
        retcode, branch, err = run_helper(
            git,
            ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=strpath,
        )
        if retcode or not branch:
            # .git/refs/remotes/origin/HEAD does not exists
            # Try HEAD
            retcode, branch, err = run_helper(
                git,
                ["symbolic-ref", "--short", "HEAD"],
                cwd=strpath,
            )
            if retcode or not branch:
                _raise(err)
        else:
            branch = branch.split(b"/", 1)[1]

        # Create local branch from remote default branch
        branch = branch.strip().decode()
        retcode, _, err = run_helper(
            git,
            ["checkout", "-b", branch, "origin/" + branch],
            cwd=strpath,
        )

        # If remote has no branches, this command always fails
        if retcode or not branch:
            # _raise(err)
            pass
        elif branch:
            # retcode, _, err = run_helper(
            # If this command fail, push won't work
            run_helper(
                git,
                ["branch", "-u", "origin/{}".format(branch)],
                cwd=strpath,
            )

        # Clone done!
        return inst

    @property
    @feature()
    def branch(self) -> str:
        retcode, out, err = self._run(["symbolic-ref", "--short", "HEAD"])

        if retcode:
            raise VCSPropertyError(
                name="branch",
                operation="get",
                raw_error=err,
            )
        return out.strip().decode()

    @branch.setter
    @feature()
    def branch(self, branchname: str):
        retcode, _, err = self._run(["checkout", branchname])

        if retcode or self.branch != branchname:
            raise VCSPropertyError(
                name="branch",
                operation="set",
                raw_error=err.decode(),
            )

    @property
    @feature()
    def branches(self) -> list:
        branches = git_get_branches(self.repodir, tag=True, remote=True)
        if branches:
            return [
                item for sublist in branches.values() if sublist is not None
                for item in sublist
            ]
        raise VCSPropertyError(name="branches", operation="get")

    @property
    @feature()
    def editable_branches(self) -> list:
        branches = git_get_branches(self.repodir)
        if branches and branches.get("branch"):
            return branches["branch"]
        raise VCSPropertyError(
            name="editable_branches",
            operation="get",
            error="Failed to get git branches.",
        )

    @feature(extra={"empty": True})
    def create_branch(self, branchname: str, empty: bool = False) -> bool:
        git = programs.find_program("git")
        if branchname in self.branches:
            raise VCSFeatureError(
                feature=self.create_branch,
                error="Failed to create branch {}"
                "since it already exists".format(branchname),
            )
        args = ["checkout"]
        if empty:
            args.extend(("--orphan", branchname))
        else:
            args.extend(("-b", branchname))

        create_retcode, _, _ = self._run(args, git=git)
        if empty and os.listdir(self.repodir) != [".git"]:
            remove_retcode, _, _ = self._run(["rm", "-rf", "."], git=git)
            return not (create_retcode or remove_retcode)
        return not create_retcode

    @feature()
    def delete_branch(self, branchname: str) -> bool:
        retcode = self._run(["branch", "-d", branchname])[0]
        return not retcode

    @property
    @feature(extra={"states": ("path", "kind", "staged")})
    def changes(self) -> Sequence[Dict[str, object]]:
        self._run(["status"], dry_run=True)
        filestates = get_git_status(self.repodir, nobranch=True)[2]
        if filestates is None:
            raise VCSPropertyError(
                name="changes",
                operation="get",
                error="Failed to get git changes",
            )
        changes = []
        for record in filestates:
            changes.extend(self._parse_change_record(record))
        return changes

    @feature(extra={"states": ("path", "kind", "staged")})
    def change(self,
               path: str,
               prefer_unstaged: bool = False) -> Dict[str, object]:
        filestates = get_git_status(self.repodir, path, nobranch=True)[2]
        if filestates is None:
            raise VCSFeatureError(
                feature=self.change,
                error="Failed to get git changes",
            )

        for record in filestates:
            changes = self._parse_change_record(record)

            if len(changes) == 2:
                return changes[not prefer_unstaged]
            if len(changes) == 1:
                return changes[0]
        return None

    @feature()
    def stage(self, path: str) -> bool:
        retcode, _, _ = self._run(["add", _escape_path(path)])
        if not osp.exists(osp.join(self.repodir, path)):
            # Assume that the file may be already staged
            retcode = 0

        if not retcode:
            change = self.change(path, prefer_unstaged=True)
            if change and change["staged"]:
                return True
        return False

    @feature()
    def unstage(self, path: str) -> bool:
        retcode, _, _ = self._run(["reset", "--", _escape_path(path)])
        if not retcode:
            change = self.change(path, prefer_unstaged=False)
            if change and not change["staged"]:
                return True
        return False

    @feature()
    def stage_all(self) -> bool:
        return self.stage(".")

    @feature()
    def unstage_all(self) -> bool:
        return self.unstage(".")

    @feature()
    def commit(self, message: str, is_path: bool = None):
        if is_path is None:
            # Check if message is a valid path
            is_path = osp.isfile(message)

        if is_path:
            retcode = self._run(["commit", "-F"], message)[0]
        else:
            args = []
            for paragraph in message.split("\n\n"):
                args.extend(("-m", paragraph))

            if not args:
                return False

            args.insert(0, "commit")
            retcode = self._run(args)[0]

        return not retcode

    @feature()
    def fetch(self, sync: bool = False) -> (int, int):
        if sync:
            self._remote_operation("fetch")
        return get_git_status(self.repodir, ".git")[1]

    @feature()
    def pull(self) -> bool:
        return self._remote_operation("pull")

    @feature()
    def push(self) -> bool:
        return self._remote_operation("push")

    @feature()
    def undo_commit(self, commits: int = 1) -> Optional[Dict[str, object]]:
        commit = None

        # prevent any float
        commits = int(commits)
        if commits < 1:
            raise ValueError(
                "Only numbers greater or equal than 1 are allowed")

        git = programs.find_program("git")

        # Get commit number
        retcode, out, err = self._run(
            ["rev-list", "HEAD", "--count", "--first-parent"],
            git=git,
        )

        if retcode:
            raise VCSFeatureError(
                feature=self.undo_commit,
                error="Failed get the number of commits in branch {}".format(
                    self.branch),
                raw_error=err.decode(),
            )

        out = out.strip(b" \n")
        if out.isdigit() and commits > int(out):
            commits = int(out) - 1

        if self.get_last_commits.enabled:
            retcode, out, err = self._run(
                [
                    "log",
                    "-1",
                    "--date=unix",
                    "--pretty=id:%h%n"
                    "author_username:%an%n"
                    "author_email:%ae%n"
                    "commit_date:%ad%n"
                    "title:%s%n"
                    "description:%n%b%x00",
                    "HEAD~" + str(commits - 1),
                ],
                git=git,
            )

            if retcode:
                # raise VCSFeatureError(
                #     feature=self.get_last_commits,
                #     error="Failed to get git history",
                #     raw_error=err.decode(),
                # )
                pass
            else:
                commit = self._parse_history_record(out.rstrip(b"\x00"))

        retcode, _, err = self._run(
            ["reset", "--soft", "HEAD~" + str(commits)], git=git)

        if retcode:
            raise VCSFeatureError(
                feature=self.get_last_commits,
                error="Failed to undo {} commits".format(commits),
                raw_error=err.decode(),
            )

        return commit

    @feature()
    def undo_change(self, path: str) -> bool:
        retcode, _, err = self._run(["checkout", "--", path])
        change = self.change(path, prefer_unstaged=True)
        if retcode:
            if change and change["kind"] == ChangedStatus.ADDED:
                # Probably it's not tracked, will remove
                os.remove(osp.join(self.repodir, path))
        else:
            if not change or change["staged"]:
                return True
        return False

    @feature()
    def undo_change_all(self) -> bool:
        return self.undo_change(".")

    @feature(
        extra={
            "attrs": ("id", "title", "description", "content",
                      "author_username", "author_email", "commit_date")
        })
    def get_last_commits(self,
                         commits: int = 1) -> Sequence[Dict[str, object]]:
        commits = int(commits)
        if commits < 1:
            raise ValueError(
                "Only numbers greater or equal than 1 are allowed")

        retcode, output, err = self._run([
            "log",
            "-" + str(commits),
            "--date=unix",
            "--pretty=id:%h%n"
            "author_username:%an%n"
            "author_email:%ae%n"
            "commit_date:%ad%n"
            "title:%s%n"
            "description:%n%b%x00",
        ])
        if retcode != 0:
            raw_err = err.decode()
            raise VCSFeatureError(
                feature=self.get_last_commits,
                error="Failed to get git history",
                raw_error=err.decode(),
            )

        return tuple(
            filter(None, (self._parse_history_record(record)
                          for record in output.split(b"\x00"))))

    @feature(extra={"branch": True})
    def tags(self) -> Sequence[str]:
        tags = git_get_branches(self.repodir, tag=True, branch=False)
        if tags:
            return tags["tag"]
        raise VCSPropertyError("tags", "get")

    # Private methods
    @staticmethod
    def _parse_change_record(record):
        changes = []
        if len(record) == 3:
            path, staged, unstaged = record
            staged, unstaged = (ChangedStatus.from_string(staged),
                                ChangedStatus.from_string(unstaged))

            if unstaged != ChangedStatus.UNCHANGED:
                changes.append(dict(path=path, kind=unstaged, staged=False))
            if staged != ChangedStatus.UNCHANGED:
                changes.append(dict(path=path, kind=staged, staged=True))

        return changes

    def _parse_history_record(self, record: bytes):
        record = record.lstrip()
        if record:
            keys = list(self.get_last_commits.extra["attrs"])
            keys.remove("description")
            history = {"description": ""}
            i = record.find(b"\ndescription:\n")

            if i != -1:
                # description parsing
                # (the description must be always in the end)
                i += 14  # len(b"\ndescription:\n")
                history["description"] = record[i:].strip(b"\x00").decode()
                record = record[:i - 14]

            for line in record.splitlines():
                if line:
                    key_to_remove = None
                    for key in keys:
                        if line.startswith(key.encode() + b":"):
                            history[key] = line[len(key) + 1:].decode()
                            key_to_remove = key
                            break
                    if key_to_remove:
                        keys.remove(key_to_remove)

            history["content"] = (history.get("title", "") + "\n" +
                                  history.get("description", ""))

            if history.get("commit_date", "").isdigit():
                history["commit_date"] = datetime.fromtimestamp(
                    int(history["commit_date"])).astimezone(timezone.utc)
            elif "commit_date" in history:
                del history["commit_date"]

            return history

        return {}

    def _remote_operation(self, operation: str, *args):
        """Helper for remote operations."""
        if platform.system() == "Windows":
            # Git for Windows uses its own credentials manager by default
            # BUG: If the credentials manager is not the default
            #      (or it requires git prompt), the operation always fail.
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GIT_ASKPASS"] = ""

            return not self._run([operation], env=env)[0]

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
                    return self._run(
                        ['config', "--local", "user.name", cred_username])[0]
            return True

        if status is False:
            # Auth failed
            raise VCSAuthError(
                credentials={
                    "username": username,
                    "password": credentials.get("password"),
                },
                credentials_callback=lambda x: setattr(self, "credentials", x),
                required_credentials=self.REQUIRED_CREDENTIALS,
                error="Wrong credentials",
            )

        raise VCSFeatureError(
            feature=getattr(self, operation),
            error="Failed to {} {} remote".format(
                operation, "to" if operation == "push" else "from"),
        )

    def _run(self,
             args: Sequence[str],
             env: Optional[Dict[str, str]] = None,
             git: Optional[str] = None,
             dry_run: bool = False) -> Tuple[int, bytes, bytes]:
        if git is None:
            git = programs.find_program("git")

            if git is None:
                # If programs.find_program fails
                raise VCSBackendFail(
                    self.repodir,
                    type(self),
                    programs=("git", ),
                )

        if not osp.exists(osp.join(self.repodir, ".git")):
            raise VCSBackendFail(
                self.repodir,
                type(self),
                is_valid_repository=False,
            )

        if dry_run:
            return None, None, None

        retcode, out, err = run_helper(git, args, cwd=self.repodir, env=env)

        # Integrity check
        if retcode is None:
            raise VCSBackendFail(self.repodir, type(self), programs=("git", ))

        return retcode, out, err


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


# Internal helpers
def run_helper(program, args, cwd=None, env=None) -> Tuple[int, bytes, bytes]:
    if program:
        try:
            proc = programs.run_program(program, args, cwd=cwd, env=env)
            output, err = proc.communicate()
            return proc.returncode, output, err

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None, None, None


def _escape_path(path: str) -> str:
    """Escape a path to be used as subprocess argument."""
    return "\\" + path if path.startswith("-") else path


# Git functions
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


def get_git_status(repopath, pathspec=".", nobranch: bool = False):
    git = programs.find_program('git')
    if git:
        try:
            proc = programs.run_program(
                git,
                [
                    "status",
                    "-z" if nobranch else "-bz",
                    "-uall",
                    "--porcelain=v1",
                    "--ignore-submodule=all",
                    _escape_path(pathspec),
                ],
                cwd=repopath,
            )
            output, _err = proc.communicate()
            if proc.returncode:
                return None, None, None

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
        else:
            changes = []
            lines = output[:-1].decode().split("\0")
            behind = ahead = 0
            local = remote = None
            if lines:
                if not nobranch:
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
                        local, remote = match.group(1, 2)
                        # behind ahead match
                        for group in match.group(3, 4):
                            if group is None:
                                pass
                            elif group.startswith("behind"):
                                behind = int(group.rsplit(" ", 1)[-1])
                            elif group.startswith("ahead"):
                                ahead = int(group.rsplit(" ", 1)[-1])

                extra_line = False
                # get branch and changes
                for line in lines:
                    if extra_line:
                        extra_line = False
                        changes[-1] = changes[-1] + (line,)
                    elif line.startswith("??"):
                        changes.append((
                            line[3:],
                            "UNCHANGED",
                            _GIT_STATUS_MAP["??"],
                        ))

                    elif "C" in line[:2] or "R" in line[:2]:
                        extra_line = True
                        changes.append((
                            line[3:],
                            _GIT_STATUS_MAP.get(line[0], "UNKNOWN"),
                            _GIT_STATUS_MAP.get(line[1], "UNKNOWN"),
                        ))
                    elif line:
                        changes.append((
                            line[3:],
                            _GIT_STATUS_MAP.get(line[0], "UNKNOWN"),
                            _GIT_STATUS_MAP.get(line[1], "UNKNOWN"),
                        ))

                if pathspec != "." and len(changes) > 1:
                    # Sum up changes in pathspec
                    final_change = [pathspec, changes[0][1], changes[0][2]]
                    for change in changes:
                        # check unstaged
                        if "MODIFIED" != final_change[1] != change[1]:
                            final_change[1] = "MODIFIED"
                        # check staged
                        if "MODIFIED" != final_change[2] != change[2]:
                            final_change[2] = "MODIFIED"
                    changes = [final_change]
                return (local, remote), (behind, ahead), changes

    return None, None, None


def git_get_branches(repopath, branch=True, tag=False, remote=False) -> list:
    git = programs.find_program('git')
    if git:
        branches = {}

        # normal branches
        if branch:
            branches["branch"] = None
            try:
                proc = programs.run_program(
                    git, ["branch", "--format", "%(refname:lstrip=2)"],
                    cwd=repopath)
                output, _ = proc.communicate()
                if proc.returncode == 0 and output:
                    branches["branch"] = output.decode().splitlines()

            except (subprocess.CalledProcessError, AttributeError, OSError):
                pass

        # tags
        if tag:
            branches["tags"] = None
            try:
                proc = programs.run_program(
                    git, ['tag', "-l", "--format", "%(refname:lstrip=2)"],
                    cwd=repopath)
                output, _ = proc.communicate()
                if proc.returncode == 0 and output:
                    branches["tags"] = output.splitlines()

            except (subprocess.CalledProcessError, AttributeError, OSError):
                pass

        # remotes
        if remote:
            branches["remotes"] = None
            try:
                proc = programs.run_program(
                    git,
                    ['branch', "-r", "-l", "--format", "%(refname:lstrip=2)"],
                    cwd=repopath)
                output, _ = proc.communicate()
                if proc.returncode == 0 and output:
                    branches["remotes"] = output.splitlines()

            except (subprocess.CalledProcessError, AttributeError, OSError):
                pass
        return branches
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
