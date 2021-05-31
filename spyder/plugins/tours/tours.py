# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Default tours."""

# Standard library imports
import sys

# Local imports
from spyder.api.translations import get_translation
from spyder.plugins.tours.api import SpyderWidgets as sw
from spyder import __docs_url__

# Localization
_ = get_translation('spyder')

# Constants
QTCONSOLE_LINK = "https://qtconsole.readthedocs.io/en/stable/index.html"
BUTTON_TEXT = ""
if sys.platform != "darwin":
    BUTTON_TEXT = ("Please click on the button below to run some simple "
                   "code in this console. This will be useful to show "
                   "you other important features.")

# This test should serve as example of keys to use in the tour frame dicts
TEST_TOUR = [
    {
        'title': "Welcome to Spyder introduction tour",
        'content': "<b>Spyder</b> is an interactive development "
                   "environment. This tip panel supports rich text. <br>"
                   "<br> it also supports image insertion to the right so far",
        'image': 'spyder_about',
    },
    {
        'title': "Widget display",
        'content': ("This shows how a widget is displayed. The tip panel "
                    "is adjusted based on the first widget in the list"),
        'widgets': ['button1'],
        'decoration': ['button2'],
        'interact': True,
    },
    {
        'title': "Widget display",
        'content': ("This shows how a widget is displayed. The tip panel "
                    "is adjusted based on the first widget in the list"),
        'widgets': ['button1'],
        'decoration': ['button1'],
        'interact': True,
    },
    {
        'title': "Widget display",
        'content': ("This shows how a widget is displayed. The tip panel "
                    "is adjusted based on the first widget in the list"),
        'widgets': ['button1'],
        'interact': True,
    },
    {
        'title': "Widget display and highlight",
        'content': "This shows how a highlighted widget looks",
        'widgets': ['button'],
        'decoration': ['button'],
        'interact': False,
    },
]


INTRO_TOUR = [
    {
        'title': _("Welcome to the introduction tour!"),
        'content': _("<b>Spyder</b> is a powerful Interactive "
                     "Development Environment (or IDE) for the Python "
                     "programming language.<br><br>"
                     "Here, we are going to guide you through its most "
                     "important features.<br><br>"
                     "Please use the arrow keys or click on the buttons "
                     "below to move along the tour."),
        'image': 'spyder_about',
    },
    {
        'title': _("Editor"),
        'content': _("This is where you write Python code before "
                     "evaluating it. You can get automatic "
                     "completions while typing, along with calltips "
                     "when calling a function and help when hovering "
                     "over an object."
                     "<br><br>The Editor comes "
                     "with a line number area (highlighted here in red) "
                     "where Spyder shows warnings and syntax errors. "
                     "They can help you to detect potential problems "
                     "before running your code.<br><br>"
                     "You can also set debug breakpoints in the line "
                     "number area by clicking next to "
                     "any non-empty line."),
        'widgets': [sw.editor],
        'decoration': [sw.editor_line_number_area],
    },
    {
        'title': _("IPython Console"),
        'content': _("This is where you can run Python code, either "
                     "from the Editor or interactively. To run the "
                     "current file, press <b>F5</b> by default, "
                     "or press <b>F9</b> to execute the current "
                     "line or selection.<br><br>"
                     "The IPython Console comes with many "
                     "useful features that greatly improve your "
                     "programming workflow, like syntax highlighting, "
                     "autocompletion, plotting and 'magic' commands. "
                     "To learn more, check out the "
                     "<a href=\"{0}\">documentation</a>."
                     "<br><br>{1}").format(QTCONSOLE_LINK, BUTTON_TEXT),
        'widgets': [sw.ipython_console],
        'run': [
            "test_list_tour = [1, 2, 3, 4, 5]",
            "test_dict_tour = {'a': 1, 'b': 2}",
        ],
    },
    {
        'title': _("Variable Explorer"),
        'content': _("In this pane you can view and edit the variables "
                     "generated during the execution of a program, or "
                     "those entered directly in the "
                     "IPython Console.<br><br>"
                     "If you ran the code in the previous step, "
                     "the Variable Explorer will show "
                     "the list and dictionary objects it generated. "
                     "By double-clicking any variable, "
                     "a new window will be opened where you "
                     "can inspect and modify their contents."),
        'widgets': [sw.variable_explorer],
        'interact': True,
    },
    {
        'title': _("Help"),
        'content': _("This pane displays documentation of the "
                     "functions, classes, methods or modules you are "
                     "currently using in the Editor or the "
                     "IPython Console."
                     "<br><br>To use it, press <b>Ctrl+I</b> "
                     "(<b>Cmd-I</b> on macOS) with the text cursor "
                     "in or next to the object you want help on."),
        'widgets': [sw.help_plugin],
        'interact': True,
    },
    {
        'title': _("Plots"),
        'content': _("This pane shows the figures and images created "
                     "during your code execution. It allows you to browse, "
                     "zoom, copy, and save the generated plots."),
        'widgets': [sw.plots_plugin],
        'interact': True,
    },
    {
        'title': _("Files"),
        'content': _("This pane lets you browse the files and "
                     "directories on your computer.<br><br>"
                     "You can open any file in its "
                     "corresponding application by double-clicking it, "
                     "and supported file types will be opened right "
                     "inside of Spyder.<br><br>"
                     "The Files pane also allows you to copy one or "
                     "many absolute or relative paths, automatically "
                     "formatted as Python strings or lists, and perform "
                     "a variety of other file operations."),
        'widgets': [sw.file_explorer],
        'interact': True,
    },
    {
        'title': _("History Log"),
        'content': _("This pane records all the commands and code run "
                     "in any IPython console, allowing you to easily "
                     "retrace your steps for reproducible research."),
        'widgets': [sw.history_log],
        'interact': True,
    },
    {
        'title': _("Find"),
        'content': _("The Find pane allows you to search for text in a "
                     "given directory and navigate through all the found "
                     "occurrences."),
        'widgets': [sw.find_plugin],
        'interact': True,
    },
    {
        'title': _("Profiler"),
        'content': _("The Profiler helps you optimize your code by "
                     "determining the run time and number of calls for "
                     "every function and method used in a file. It also "
                     "allows you to save and compare your results between "
                     "runs."),
        'widgets': [sw.profiler],
        'interact': True,
    },
    {
        'title': _("Code Analysis"),
        'content': _("The Code Analysis helps you improve the quality of "
                     "your programs by detecting style issues, bad practices "
                     "and potential bugs."),
        'widgets': [sw.code_analysis],
        'interact': True
    },
    {
        'title': _("The end"),
        'content': _('You have reached the end of our tour and are '
                     'ready to start using Spyder! For more '
                     'information, check out our '
                     '<a href="{}">documentation</a>.'
                     '<br><br>').format(__docs_url__),
        'image': 'spyder_about'
    },
]


FEAT30 = [
    {
        'title': _("New features in Spyder 3.0"),
        'content': _("<b>Spyder</b> is an interactive development "
                     "environment based on bla"),
        'image': 'spyder_about',
    },
    {
        'title': _("Welcome to Spyder introduction tour"),
        'content': _("Spyder is an interactive development environment "
                     "based on bla"),
        'widgets': ['variableexplorer'],
    },
]


class TourIdentifiers:
    IntroductionTour = "introduction_tour"
    TestTour = "test_tour"
