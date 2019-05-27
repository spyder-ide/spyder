#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Script and functions to automatically remove trailing spaces from files."""

# Standard library imports
import argparse
import datetime
import re
import subprocess
import sys
import warnings

# Third party imports
import requests


PR_DATE_CUTOFF = datetime.datetime(2018, 12, 8, 0)
INCLUDE_EXTENSIONS = {"bat", "c", "cpp", "css", "csv", "gitignore",
                      "gitattributes", "html", "in", "ini", "js", "md", "py",
                      "pyx", "qss", "R", "rst", "sh", "txt", "xml", "yml"}
EXCLUDE_PATHS = [
    "/tests?/(?!(tests?_|__init__|fixture))",  # Skip all test datafiles
    "/mathjax/",  # Mathjax is vendored code and should be left as is
    r"^\.github/ISSUE_TEMPLATE\.md$",  # Ws needed before bullets
    r"^spyder/defaults/.*\.ini$",  # Could break ancient Spyder versions
    "^CHANGELOG.md$",  # Don't remove ws in the changelog, for some reason
    ]


def git_files(file_types):
    """Get index, staged, or modified files from git."""
    files_final = set()
    git_commands = {
        "staged": ("git", "diff", "--name-only", "--cached",
                   "--diff-filter=d", "-z"),
        "unstaged": ("git", "diff", "--name-only", "--diff-filter=d", "-z"),
        "untracked": ("git", "ls-files", "-o", "--exclude-standard", "-z"),
        "index": ("git", "ls-files", "--cached", "--exclude-standard", "-z"),
        }

    for file_type in file_types:
        try:
            status_output = subprocess.run(git_commands[file_type],
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           check=True,
                                           encoding="utf-8")
        # If not inside the repo or git otherwise runs into a problem
        except subprocess.CalledProcessError as e:
            raise RuntimeError("Must be in the root of a Git repo") from e
        # If subprocess.run doesn't exist or doesn't have the encoding arg
        except (TypeError, AttributeError):
            raise RuntimeError("Python >=3.6 required to run script.")
        if status_output.stdout:
            files_final = files_final.union(
                set(status_output.stdout.strip("\0").split("\0")))
        else:
            files_final = set()
    return files_final


def filter_files(file_paths, include_extensions=INCLUDE_EXTENSIONS,
                 exclude_paths=EXCLUDE_PATHS):
    """Filter files by extension and path."""
    filtered_paths = {file_path for file_path in file_paths
                      if file_path.split(".")[-1] in include_extensions}
    exclude_paths_regex = re.compile("|".join(exclude_paths))
    filtered_paths = {file_path for file_path in filtered_paths
                      if not exclude_paths_regex.search(file_path)}
    return filtered_paths


def get_github_prs(repo_path=None):
    """Get the files touched by open PRs on the given repo."""
    pr_api_url = "https://api.github.com/repos/{repo_path}/pulls"

    if repo_path is None:
        status_output = subprocess.run(
            ["git", "remote", "get-url", "upstream"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if not status_output.stdout:
            status_output = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8")
            if not status_output.stdout:
                raise ValueError("Repo path not provided and could not be "
                                 "determined via git remote origin/upstream.")
        repo_path = "/".join(
            status_output.stdout.split(":")[1].split("/")[-2:]).split(".")[0]

    pr_api_url = pr_api_url.format(repo_path=repo_path)
    pr_params = {"status": "open", "per_page": 99}
    pr_responce = requests.get(pr_api_url, pr_params)
    pr_responce.raise_for_status()
    open_prs = pr_responce.json()

    open_prs = [pr for pr in open_prs if datetime.datetime.strptime(
        pr["created_at"], "%Y-%m-%dT%H:%M:%SZ") >= PR_DATE_CUTOFF]

    return open_prs


def checkout_branch(branch="master"):
    """Checkout the given branch, creating it if it does not already exist."""
    status_output = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    previous_branch = status_output.stdout.strip()
    status_output = subprocess.run(["git", "rev-parse", "--verify", branch],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   encoding="utf-8")
    if status_output.stdout:
        subprocess.run(["git", "checkout", branch])
    else:
        subprocess.run(["git", "checkout", "-b", branch])

    return previous_branch


def get_pr_merge_conflicts(prs_tocheck, branch_to_compare="master"):
    """Determine the files that would have conflicts with a certain branch."""
    merge_conflicts_bypr = {}
    previous_branch = checkout_branch(branch=branch_to_compare)

    for pr in prs_tocheck:
        try:
            subprocess.run(["git", "pr", str(pr["number"])], check=True)
        except subprocess.CalledProcessError:
            warnings.warn("git pr failed; installing git pr alias.")
            subprocess.run(
                ["git", "config", "--local", "alias.pr",
                 ("!f() { git fetch -fu "
                  "${2:-$(git remote |grep ^upstream || echo origin)} "
                  "refs/pull/$1/head:pr/$1 && git checkout pr/$1; }; f")])
            subprocess.run(["git", "pr", str(pr["number"])], check=True)

        subprocess.run(["git", "checkout", branch_to_compare])
        subprocess.run(["git", "merge", "--no-commit", "--no-ff",
                        "pr/" + str(pr["number"])])
        status_output = subprocess.run(
            ["git", "ls-files", "-u", "--exclude-standard", "-z"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if status_output.stdout:
            merge_conflicts = {file_data.split("\t")[-1] for file_data in
                               status_output.stdout.strip("\0").split("\0")}
        else:
            merge_conflicts = set()
        subprocess.run(["git", "merge", "--abort"])
        merge_conflicts_bypr[pr["number"]] = merge_conflicts

    try:
        subprocess.run(["git", "pr-clean"], check=True)
    except subprocess.CalledProcessError:
        warnings.warn("git pr-clean failed; installing git pr-clean alias.")
        subprocess.run(
            ["git", "config", "--local", "alias.pr-clean",
             ("!git for-each-ref refs/heads/pr/* --format='%(refname)' "
              "| while read ref ; do branch=${ref#refs/heads/} ; "
              "git branch -D $branch ; done")])
        subprocess.run(["git", "pr-clean"])
    subprocess.run(["git", "checkout", previous_branch])
    return merge_conflicts_bypr


def handle_whitespace(file_paths, whitespace_type="all", warn_only=False,
                      verbose=False):
    """Detect or eliminate whitespace in the passed files."""
    if verbose is False and warn_only:
        verbose = 2
    if verbose:
        print("{action} {ws_type} whitespace in the following files:".format(
            action=("Detected" if warn_only else "Removed"),
            ws_type=whitespace_type))
    found_files = {}
    if whitespace_type == "blank":
        space_regex = (re.compile(r"\n[ \t]+\n"), r"\n\n")
    elif whitespace_type == "trailing":
        space_regex = (re.compile(r"([^ \t])[ \t]+\n"), r"\1\n")
    elif whitespace_type == "both":
        space_regex = (re.compile(r"[ \t]+\n"), r"\n")
    else:
        raise ValueError(
            "handle_type must be one of 'blank', 'trailing' or 'all'")

    for file_path in file_paths:
        try:
            with open(file_path, mode="r", encoding="utf-8") as file:
                file_contents = file.read()
                newline_char = file.newlines
        except (OSError, UnicodeError, IOError) as e:
            warnings.warn("{e_type} reading file {fname}: {e_msg}".format(
                e_type=type(e), fname=file_path, e_msg=str(e)))
            continue
        output_contents, n_subs = re.subn(*space_regex, file_contents)
        if n_subs:
            if verbose >= 2:
                print("{ws_count} : {file_path}".format(
                    ws_count=n_subs, file_path=file_path))
            if not warn_only:
                try:
                    with open(file_path, mode="w", encoding="utf-8",
                              newline=newline_char) as file:
                        file_contents = file.write(output_contents)
                except (OSError, UnicodeError, IOError) as e:
                    warnings.warn("{e_type} reading file {fname}: {e_msg}"
                                  .format(e_type=type(e), fname=file_path,
                                          e_msg=str(e)))
                    continue
            found_files[file_path] = n_subs
    if verbose:
        if found_files:
            print("{n_ws} instances in {n_files} file(s)".format(
                n_ws=sum(found_files.values()),
                n_files=len(found_files)))
        else:
            print("No matching whitespace found.")

    return found_files


def handle_whitespace_files(file_types, whitespace_type="all",
                            warn_only=False, verbose=False,
                            check_prs=False):
    """Remove trailing whitespace in all or selected files in the projct."""
    files_toprocess = git_files(file_types)
    files_toprocess = filter_files(files_toprocess)

    if check_prs:
        open_prs = get_github_prs()
        conflicts_before = get_pr_merge_conflicts(open_prs, "master")
        temp_branch_name = "temp-test-nospace"
        previous_branch = checkout_branch(branch=temp_branch_name)
        handle_whitespace(files_toprocess, whitespace_type=whitespace_type,
                          warn_only=False, verbose=0)
        subprocess.run(["git", "commit", "-a", "-m", "test"])
        conflicts_after = get_pr_merge_conflicts(open_prs, temp_branch_name)

        all_conflicts = set()
        conflicts_bypr = {}
        for pr in open_prs:
            whitespace_conflicts = conflicts_after[pr["number"]].difference(
                conflicts_before[pr["number"]])
            if whitespace_conflicts:
                conflicts_bypr[pr["number"]] = whitespace_conflicts
                all_conflicts = all_conflicts.union(whitespace_conflicts)
                if verbose >= 2:
                    print("PR #{pr_num} has conflicts {conf}".format(
                        pr_num=pr["number"], conf=whitespace_conflicts))
        if verbose:
            print("Total conflicts: {num_conf} in {num_prs} PRs".format(
                num_conf=len(all_conflicts), num_prs=len(conflicts_bypr)))
        subprocess.run(["git", "checkout", previous_branch])
        subprocess.run(["git", "branch", "-D", temp_branch_name])
        files_toprocess = files_toprocess.difference(all_conflicts)

    found_files = handle_whitespace(
        files_toprocess, whitespace_type=whitespace_type,
        warn_only=warn_only, verbose=verbose)

    if check_prs:
        found_files = (found_files, conflicts_bypr)

    return found_files


def generate_arg_parser():
    """Generate the argument parser for the trailing whitespace script."""
    description = "Automatically remove trailing whitespace from files."
    arg_parser = argparse.ArgumentParser(description=description)

    arg_parser.add_argument(
        "--whitespace-type", default="both",
        help=("Type of whitespace to remove. 'blank' for just whitespace on "
              "otherwise-blank lines, 'trailing' for whitespace on non-empty "
              "lines, and 'both' to remove both (the default)."))

    arg_parser.add_argument(
        "--file-types", default=["staged", "unstaged", "untracked"], nargs="*",
        help=("Type(s) of files to process, as determined by git. "
              "Options are 'staged', 'unstaged', 'untracked' and 'index' "
              "(to process the entire git index). "
              "By default, does the first 3 to capture all modified files, "
              "whether or not they are staged."))

    arg_parser.add_argument(
        "--warn-only", action="store_true",
        help=("If passed, will only warn (and exit with a non-zero status) "
              "if trailing spaces are found in the files, rather than "
              "removing them. Intended for a CI-side check. "
              "Also implictly triggers verbosity=2."))

    arg_parser.add_argument(
        "--verbose", "-v", action="count",
        help=("How much detail to print about the files converted. "
              "At verbosity level 0 (the default), nothing is printed. "
              "At level 1 (-v), prints a summary of trailing spaces and "
              "conflicts detected across all files. At level 2, (-vv), "
              "prints detailed information about every file and conflict."))

    arg_parser.add_argument(
        "--check-prs", action="store_true",
        help=("If passed, will check the changes to see if they cause "
              "merge conflicts on any open PRs on the repo, and only "
              "make them in the files that do not result in such. "
              "Installs the ``pr`` and ``pr-clean`` git alises if not found."))

    return arg_parser


if __name__ == "__main__":
    arg_parser = generate_arg_parser()
    script_args = arg_parser.parse_args()
    found_files = handle_whitespace_files(**script_args.__dict__)
    if found_files and script_args.warn_only:
        sys.exit(1)
    else:
        sys.exit(0)
