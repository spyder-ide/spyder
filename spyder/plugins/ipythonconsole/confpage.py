# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""IPython Console config page."""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                            QVBoxLayout)

# Local imports
from spyder.api.translations import _
from spyder.api.preferences import PluginConfigPage


class IPythonConsoleConfigPage(PluginConfigPage):

    def setup_page(self):
        newcb = self.create_checkbox

        # Display group
        display_group = QGroupBox(_("Display"))
        banner_box = newcb(_("Display initial banner"), 'show_banner',
                           tip=_("This option lets you hide the message "
                                 "shown at\nthe top of the console when "
                                 "it's opened."))
        calltips_box = newcb(_("Show calltips"), 'show_calltips')
        show_time_box = newcb(_("Show elapsed time"), 'show_elapsed_time')

        display_layout = QVBoxLayout()
        display_layout .addWidget(banner_box)
        display_layout .addWidget(calltips_box)
        display_layout.addWidget(show_time_box)
        display_group.setLayout(display_layout)

        # Confirmations group
        confirmations_group = QGroupBox(_("Confirmations"))
        ask_box = newcb(
            _("Ask for confirmation before closing"), 'ask_before_closing'
        )
        reset_namespace_box = newcb(
            _("Ask for confirmation before removing all user-defined "
              "variables"),
            'show_reset_namespace_warning',
            tip=_("This option lets you hide the warning message shown\n"
                  "when resetting the namespace from Spyder.")
        )
        ask_restart_box = newcb(
            _("Ask for confirmation before restarting"),
            'ask_before_restart',
            tip=_("This option lets you hide the warning message shown\n"
                  "when restarting the kernel.")
        )

        confirmations_layout = QVBoxLayout()
        confirmations_layout.addWidget(ask_box)
        confirmations_layout.addWidget(reset_namespace_box)
        confirmations_layout.addWidget(ask_restart_box)
        confirmations_group.setLayout(confirmations_layout)

        comp_group = QGroupBox(_("Completion type"))
        comp_label = QLabel(_("Decide what type of completion to use"))
        comp_label.setWordWrap(True)
        completers = [(_("Graphical"), 0), (_("Terminal"), 1), (_("Plain"), 2)]
        comp_box = self.create_combobox(_("Completion:")+"   ", completers,
                                        'completion_type')

        comp_layout = QVBoxLayout()
        comp_layout.addWidget(comp_label)
        comp_layout.addWidget(comp_box)
        comp_group.setLayout(comp_layout)

        # Source Code Group
        source_code_group = QGroupBox(_("Source code"))

        # Note: The maximum here is set to a relatively small value because
        # larger ones make Spyder sluggish.
        # Fixes spyder-ide/spyder#19091
        buffer_spin = self.create_spinbox(
                _("Buffer:  "), _(" lines"),
                'buffer_size', min_=-1, max_=5000, step=100,
                tip=_("Set the maximum number of lines of text shown in the\n"
                      "console before truncation. Specifying -1 disables it\n"
                      "(not recommended!)"))

        source_code_layout = QVBoxLayout()
        source_code_layout.addWidget(buffer_spin)
        source_code_group.setLayout(source_code_layout)

        # --- Graphics ---
        # Pylab Group
        pylab_group = QGroupBox(_("Support for graphics (Matplotlib)"))
        pylab_box = newcb(_("Activate support"), 'pylab')
        autoload_pylab_box = newcb(
            _("Automatically load Matplotlib and NumPy modules"),
            'pylab/autoload',
            tip=_(
                "This lets you generate graphics and work with arrays "
                "<b>without</b> importing the commands to do it. It's also "
                "useful to develop GUIs with Spyder."
            )
        )
        autoload_pylab_box.setEnabled(self.get_option('pylab'))
        pylab_box.checkbox.toggled.connect(autoload_pylab_box.setEnabled)

        pylab_layout = QVBoxLayout()
        pylab_layout.addWidget(pylab_box)
        pylab_layout.addWidget(autoload_pylab_box)
        pylab_group.setLayout(pylab_layout)

        # Pylab backend Group
        inline = _("Inline")
        automatic = _("Automatic")
        backend_group = QGroupBox(_("Graphics backend"))
        bend_label = QLabel(_("Decide how Matplotlib graphics are displayed"))

        backends = [
            (inline, 'inline'),
            (automatic, 'auto'),
            ("Qt", 'qt'),
            ("Tk", 'tk')
        ]

        if sys.platform == 'darwin':
            backends.append(("macOS", 'osx'))
        backends = tuple(backends)

        backend_box = self.create_combobox(
            _("Backend:") + "   ",
            backends,
            'pylab/backend', default='inline',
            tip=_(
                "If unsure, select <b>%s</b> to put graphics in the Plots "
                "pane or <b>%s</b> to interact with them (through zooming and "
                "panning) in a separate window."
            ) % (inline, automatic)
        )

        backend_layout = QVBoxLayout()
        backend_layout.addWidget(bend_label)
        backend_layout.addWidget(backend_box)
        backend_group.setLayout(backend_layout)
        backend_group.setEnabled(self.get_option('pylab'))
        pylab_box.checkbox.toggled.connect(backend_group.setEnabled)

        # Inline backend Group
        inline_group = QGroupBox(_("Inline backend"))
        inline_label = QLabel(_("Decide how to render the figures created by "
                                "this backend"))
        inline_label.setWordWrap(True)
        formats = (("PNG", 'png'), ("SVG", 'svg'))
        format_box = self.create_combobox(_("Format:")+"   ", formats,
                                          'pylab/inline/figure_format',
                                          default='png')
        resolution_spin = self.create_spinbox(
                        _("Resolution:")+"  ", " "+_("dpi"),
                        'pylab/inline/resolution', min_=50, max_=999, step=0.1,
                        tip=_("Only used when the format is PNG. Default is "
                              "72"))
        width_spin = self.create_spinbox(
                          _("Width:")+"  ", " "+_("inches"),
                          'pylab/inline/width', min_=2, max_=20, step=1,
                          tip=_("Default is 6"))
        height_spin = self.create_spinbox(
                          _("Height:")+"  ", " "+_("inches"),
                          'pylab/inline/height', min_=1, max_=20, step=1,
                          tip=_("Default is 4"))
        fontsize_spin = self.create_spinbox(
            _("Font size:") + "  ",
            " " + _("points"),
            'pylab/inline/fontsize',
            min_=5,
            max_=48,
            step=1.0,
            tip=_("Default is 10")
        )
        bottom_spin = self.create_spinbox(
            _("Bottom edge:") + "  ",
            " " + _("of figure height"),
            'pylab/inline/bottom',
            min_=0,
            max_=0.3,
            step=0.01,
            tip=_("The position of the bottom edge of the subplots,\nas a "
                  "fraction of the figure height.\nThe default is 0.11.")
        )
        bottom_spin.spinbox.setDecimals(2)
        bbox_inches_box = newcb(
            _("Use a tight layout for inline plots"),
            'pylab/inline/bbox_inches',
            tip=_("Sets bbox_inches to \"tight\" when\n"
                  "plotting inline with matplotlib.\n"
                  "When enabled, can cause discrepancies\n"
                  "between the image displayed inline and\n"
                  "that created using savefig."))

        inline_v_layout = QVBoxLayout()
        inline_v_layout.addWidget(inline_label)
        inline_layout = QGridLayout()
        inline_layout.addWidget(format_box.label, 1, 0)
        inline_layout.addWidget(format_box.combobox, 1, 1)

        spinboxes = [resolution_spin, width_spin, height_spin,
                     fontsize_spin, bottom_spin]
        for counter, spinbox in enumerate(spinboxes):
            inline_layout.addWidget(spinbox.plabel, counter + 2, 0)
            inline_layout.addWidget(spinbox.spinbox, counter + 2, 1)
            inline_layout.addWidget(spinbox.slabel, counter + 2, 2)
            inline_layout.addWidget(spinbox.help_label, counter + 2, 3)

        inline_layout.addWidget(bbox_inches_box, len(spinboxes) + 2, 0, 1, 4)

        inline_h_layout = QHBoxLayout()
        inline_h_layout.addLayout(inline_layout)
        inline_h_layout.addStretch(1)
        inline_v_layout.addLayout(inline_h_layout)
        inline_group.setLayout(inline_v_layout)
        inline_group.setEnabled(self.get_option('pylab'))
        pylab_box.checkbox.toggled.connect(inline_group.setEnabled)

        # --- Startup ---
        # Run lines Group
        run_lines_group = QGroupBox(_("Run code"))
        run_lines_label = QLabel(_("You can run several lines of code when "
                                   "a console is started. Please introduce "
                                   "each one separated by semicolons and a "
                                   "space, for example:<br>"
                                   "<i>import os; import sys</i>"))
        run_lines_label.setWordWrap(True)
        run_lines_edit = self.create_lineedit(_("Lines:"), 'startup/run_lines',
                                              '', alignment=Qt.Horizontal)

        run_lines_layout = QVBoxLayout()
        run_lines_layout.addWidget(run_lines_label)
        run_lines_layout.addWidget(run_lines_edit)
        run_lines_group.setLayout(run_lines_layout)

        # Run file Group
        run_file_group = QGroupBox(_("Run a file"))
        run_file_label = QLabel(_("You can also run a whole file at startup "
                                  "instead of just some lines (This is "
                                  "similar to have a PYTHONSTARTUP file)."))
        run_file_label.setWordWrap(True)
        file_radio = newcb(_("Use the following file:"),
                           'startup/use_run_file', False)
        run_file_browser = self.create_browsefile('', 'startup/run_file', '')
        run_file_browser.setEnabled(False)
        file_radio.checkbox.toggled.connect(run_file_browser.setEnabled)

        run_file_layout = QVBoxLayout()
        run_file_layout.addWidget(run_file_label)
        run_file_layout.addWidget(file_radio)
        run_file_layout.addWidget(run_file_browser)
        run_file_group.setLayout(run_file_layout)

        # ---- Advanced settings ----
        # Enable Jedi completion
        jedi_group = QGroupBox(_("Jedi completion"))
        jedi_label = QLabel(_("Enable Jedi-based <tt>Tab</tt> completion "
                              "in the IPython console; similar to the "
                              "greedy completer, but without evaluating "
                              "the code.<br>"
                              "<b>Warning:</b> Slows down your console "
                              "when working with large dataframes!"))
        jedi_label.setWordWrap(True)
        jedi_box = newcb(_("Use Jedi completion in the IPython console"),
                         "jedi_completer",
                         tip=_("<b>Warning</b>: "
                               "Slows down your console when working with "
                               "large dataframes!<br>"
                               "Allows completion of nested lists etc."))

        jedi_layout = QVBoxLayout()
        jedi_layout.addWidget(jedi_label)
        jedi_layout.addWidget(jedi_box)
        jedi_group.setLayout(jedi_layout)

        # Greedy completer group
        greedy_group = QGroupBox(_("Greedy completion"))
        greedy_label = QLabel(_("Enable <tt>Tab</tt> completion on elements "
                                "of lists, results of function calls, etc, "
                                "<i>without</i> assigning them to a variable, "
                                "like <tt>li[0].&lt;Tab&gt;</tt> or "
                                "<tt>ins.meth().&lt;Tab&gt;</tt> <br>"
                                "<b>Warning:</b> Due to a bug, IPython's "
                                "greedy completer requires a leading "
                                "<tt>&lt;Space&gt;</tt> for some completions; "
                                "e.g.  <tt>np.sin(&lt;Space&gt;np.&lt;Tab&gt;"
                                "</tt> works while <tt>np.sin(np.&lt;Tab&gt; "
                                "</tt> doesn't.<br><br>"))
        greedy_label.setWordWrap(True)
        greedy_box = newcb(_("Use greedy completion in the IPython console"),
                           "greedy_completer",
                           tip="<b>Warning</b>: It can be unsafe because the "
                               "code is actually evaluated when you press "
                               "<tt>Tab</tt>.")

        greedy_layout = QVBoxLayout()
        greedy_layout.addWidget(greedy_label)
        greedy_layout.addWidget(greedy_box)
        greedy_group.setLayout(greedy_layout)

        # Autocall group
        autocall_group = QGroupBox(_("Autocall"))
        autocall_label = QLabel(_("Autocall makes IPython automatically call "
                                  "any callable object even if you didn't "
                                  "type explicit parentheses.<br>"
                                  "For example, if you type <i>str 43</i> it "
                                  "becomes <i>str(43)</i> automatically."))
        autocall_label.setWordWrap(True)

        smart = _('Smart')
        full = _('Full')
        autocall_opts = ((_('Off'), 0), (smart, 1), (full, 2))
        autocall_box = self.create_combobox(
                       _("Autocall:  "), autocall_opts, 'autocall', default=0,
                       tip=_("On <b>%s</b> mode, Autocall is not applied if "
                             "there are no arguments after the callable. On "
                             "<b>%s</b> mode, all callable objects are "
                             "automatically called (even if no arguments are "
                             "present).") % (smart, full))

        autocall_layout = QVBoxLayout()
        autocall_layout.addWidget(autocall_label)
        autocall_layout.addWidget(autocall_box)
        autocall_group.setLayout(autocall_layout)

        # Autoreload group
        autoreload_group = QGroupBox(_("Autoreload"))
        autoreload_label = QLabel(
            _("Autoreload reloads modules automatically every time before "
              "executing your Python code.<br>"
              "This is a different mechanism than the User Module Reloader "
              "(UMR) and it can be slow on Windows due to limitations of its "
              "file system."
            )
        )
        autoreload_label.setWordWrap(True)

        autoreload_box = newcb(
            _("Use autoreload"),
            "autoreload",
            tip=_(
                "This option enables the autoreload magic.<br>"
                "Please refer to its documentation to learn how to use it."
            )
        )

        autoreload_layout = QVBoxLayout()
        autoreload_layout.addWidget(autoreload_label)
        autoreload_layout.addWidget(autoreload_box)
        autoreload_group.setLayout(autoreload_layout)

        # Sympy group
        sympy_group = QGroupBox(_("Symbolic mathematics"))
        sympy_label = QLabel(_("Perfom symbolic operations in the console "
                               "(e.g. integrals, derivatives, vector "
                               "calculus, etc) and get the outputs in a "
                               "beautifully printed style (it requires the "
                               "Sympy module)."))
        sympy_label.setWordWrap(True)
        sympy_box = newcb(_("Use symbolic math"), "symbolic_math",
                          tip=_("This option loads the Sympy library to work "
                                "with.<br>Please refer to its documentation "
                                "to learn how to use it."))

        sympy_layout = QVBoxLayout()
        sympy_layout.addWidget(sympy_label)
        sympy_layout.addWidget(sympy_box)
        sympy_group.setLayout(sympy_layout)

        # Prompts group
        prompts_group = QGroupBox(_("Prompts"))
        prompts_label = QLabel(_("Modify how Input and Output prompts are "
                                 "shown in the console."))
        prompts_label.setWordWrap(True)
        in_prompt_edit = self.create_lineedit(
            _("Input prompt:"),
            'in_prompt', '',
            _('Default is<br>'
              'In [&lt;span class="in-prompt-number"&gt;'
              '%i&lt;/span&gt;]:'),
            alignment=Qt.Horizontal)
        out_prompt_edit = self.create_lineedit(
            _("Output prompt:"),
            'out_prompt', '',
            _('Default is<br>'
              'Out[&lt;span class="out-prompt-number"&gt;'
              '%i&lt;/span&gt;]:'),
            alignment=Qt.Horizontal)

        prompts_g_layout = QGridLayout()
        prompts_g_layout.addWidget(in_prompt_edit.label, 0, 0)
        prompts_g_layout.addWidget(in_prompt_edit.textbox, 0, 1)
        prompts_g_layout.addWidget(in_prompt_edit.help_label, 0, 2)
        prompts_g_layout.addWidget(out_prompt_edit.label, 1, 0)
        prompts_g_layout.addWidget(out_prompt_edit.textbox, 1, 1)
        prompts_g_layout.addWidget(out_prompt_edit.help_label, 1, 2)

        prompts_layout = QVBoxLayout()
        prompts_layout.addWidget(prompts_label)
        prompts_layout.addLayout(prompts_g_layout)
        prompts_group.setLayout(prompts_layout)

        # Windows adjustments
        windows_group = QGroupBox(_("Windows adjustments"))
        hide_cmd_windows = newcb(
            _("Hide command line output windows "
              "generated by the subprocess module."),
            'hide_cmd_windows')
        windows_layout = QVBoxLayout()
        windows_layout.addWidget(hide_cmd_windows)
        windows_group.setLayout(windows_layout)

        # --- Tabs organization ---
        self.create_tab(
            _("Interface"),
            [display_group, confirmations_group, comp_group, source_code_group]
        )

        self.create_tab(
            _("Graphics"),
            [pylab_group, backend_group, inline_group]
        )

        self.create_tab(
            _("Startup"),
            [run_lines_group, run_file_group]
        )

        self.create_tab(
            _("Advanced settings"),
            [jedi_group, greedy_group, autocall_group, autoreload_group,
             sympy_group, prompts_group, windows_group]
        )
