# -*- coding: utf-8 -*-
#
# Copyright © 2015 The Spyder Developmet Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Build a list of issues per milestone

NOTE: This script works with githupy, not with PyGithub!

To install it just run

    pip install githubpy
"""

# Std imports
import argparse
import sys

# Local imports
import github

# Cli options
parser = argparse.ArgumentParser(description='Script to print the list of '
                                 'issues and pull requests closed in a given '
                                 'milestone')
parser.add_argument('-m', action="store", dest="milestone", default='',
                    help='Milestone')
parser.add_argument('-f', action="store", dest="format", default='changelog',
                    help="Format for print, either 'changelog' (for our "
                         "Changelog.md file) or 'release' (for the Github "
                         "Releases page)")
results = parser.parse_args()

# Creating the main class to interact with Github
gh = github.GitHub()
repo = gh.repos('spyder-ide')('spyder')

if not results.milestone:
    print('Please pass a milestone to this script. See its help')
    sys.exit(1)

# Get milestone number, given its name
milestones = repo.milestones.get()
milestone_number = -1
for ms in milestones:
    if ms['title'] == results.milestone:
        milestone_number = ms['number']

if milestone_number == -1:
    print("You didn't pass a valid milestone name!")
    sys.exit(1)

# This returns issues and pull requests
issues = repo.issues.get(milestone=milestone_number, state='closed',
                         per_page='500')

# Printing issues
print('\n**Issues**\n')
number_of_issues = 0
for i in issues:
    pr = i.get('pull_request', '')
    if not pr:
        number_of_issues += 1
        number = i['number']
        if results.format == 'changelog':
            issue_link = "* [Issue %d](/spyder-ide/spyder/issues/%d)" % (number,
                                                                         number)
        else:
            issue_link = "* Issue #%d" % number
        print(issue_link + ' - ' + i['title'])
print('\nIn this release they were closed %d issues' % number_of_issues)

# Printing pull requests
print('\n**Pull requests**\n')
number_of_prs = 0
for i in issues:
    pr = i.get('pull_request', '')
    if pr:
        number_of_prs += 1
        number = i['number']
        if results.format == 'changelog':
            pr_link = "* [PR %d](/spyder-ide/spyder/pull/%d)" % (number,
                                                                 number)
        else:
            pr_link = "* PR #%d" % number
        print(pr_link + ' - ' + i['title'])
print('\nIn this release they were merged %d pull requests' % number_of_prs)
