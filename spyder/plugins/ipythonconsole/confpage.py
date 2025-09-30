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
from qtpy.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

# Local imports
from spyder.api.translations import _
from spyder.api.preferences import PluginConfigPage


class IPythonConsoleConfigPage(PluginConfigPage):

    def __init__(self, plugin, parent):
        super().__init__(plugin, parent)

        self.buffer_spin = None
        self.apply_callback = self.warn_if_large_buffer

    def setup_page(self):
        newcb = self.create_checkbox

        # Display group
        display_group = QGroupBox(_("Display"))
        banner_box = newcb(
            _("Show welcome message"),
            'show_banner',
            tip=_("Print the startup message when opening a new console"),
        )
        calltips_box = newcb(
            _("Show calltips"),
            'show_calltips',
            tip=_("Show a summary help popup when typing an open parenthesis "
                  "after a callable function"),
        )
        show_time_box = newcb(
            _("Show elapsed time"),
            'show_elapsed_time',
            tip=_("Display the time since the current console was started "
                  "in the tab bar"),
        )

        display_layout = QVBoxLayout()
        display_layout.addWidget(banner_box)
        display_layout.addWidget(calltips_box)
        display_layout.addWidget(show_time_box)
        display_group.setLayout(display_layout)

        # Confirmation group
        confirmations_group = QGroupBox(_("Confirmation"))
        ask_box = newcb(
            _("Ask for confirmation before closing"),
            'ask_before_closing',
        )
        reset_namespace_box = newcb(
            _("Ask for confirmation before removing all variables"),
            'show_reset_namespace_warning',
        )
        ask_restart_box = newcb(
            _("Ask for confirmation before restarting"),
            'ask_before_restart',
        )

        confirmations_layout = QVBoxLayout()
        confirmations_layout.addWidget(ask_box)
        confirmations_layout.addWidget(ask_restart_box)
        confirmations_layout.addWidget(reset_namespace_box)
        confirmations_group.setLayout(confirmations_layout)

        # Completion group
        comp_group = QGroupBox(_("Completion"))
        completers = [(_("Graphical"), 0), (_("Terminal"), 1), (_("Plain"), 2)]
        comp_box = self.create_combobox(
            _("Display:"),
            completers,
            'completion_type',
            tip=_(
                "Graphical shows a list of completion matches in a GUI.\n"
                "Plain displays matches in the Console output, like Bash.\n"
                "Terminal is Plain plus Tab selecting matches, like Zsh.\n"
            ),
        )
        jedi_box = newcb(
            _("Use Jedi completion"),
            "jedi_completer",
            tip=_(
                "Enable Jedi-based tab-completion in the IPython console.\n"
                "Similar to the greedy completer, but without evaluating "
                "the code and allows completion of dictionary keys, "
                "nested lists and similar.\n"
                "Warning: Can slow down the Console when working with "
                "large dataframes."
            ),
        )
        greedy_box = newcb(
            _("Use greedy completion"),
            "greedy_completer",
            tip=_(
                "Enable <tt>Tab</tt> completion on elements of lists, "
                "results of function calls and similar "
                "<i>without</i> assigning them to a variable, "
                "like <tt>li[0].&lt;Tab&gt;</tt> or "
                "<tt>ins.meth().&lt;Tab&gt;</tt><br>"
                "<b>Warning</b>: This can be unsafe because your code "
                "is actually executed when you press <tt>Tab</tt>."
            ),
        )

        comp_layout = QVBoxLayout()
        comp_layout.addWidget(comp_box)
        comp_layout.addWidget(jedi_box)
        comp_layout.addWidget(greedy_box)
        comp_group.setLayout(comp_layout)

        # Output group
        output_group = QGroupBox(_("Output"))
        self.buffer_spin = self.create_spinbox(
            _("Buffer:"),
            _(" lines"),
            'buffer_size',
            min_=100,
            # >10k can make Spyder slow, see spyder-ide/spyder#19091
            max_=50_000,
            step=100,
            tip=_(
                "The maximum number of output lines "
                "retained in each console at a time.\n"
                "Warning; Buffer sizes greater than 10000 lines can slow "
                "down Spyder."
            ),
        )
        sympy_box = newcb(
            _("Render SymPy symbolic math"),
            "symbolic_math",
            tip=_(
                "Pretty-print the outputs of SymPy symbolic computations\n"
                "(requires SymPy installed in the console environment).\n"
                "Refer to SymPy's documentation for details on using it."
            ),
        )

        output_layout = QVBoxLayout()
        output_layout.addWidget(self.buffer_spin)
        output_layout.addWidget(sympy_box)
        output_group.setLayout(output_layout)

        # --- Plotting ---
        # Matplotlib group
        matplotlib_group = QGroupBox(_("Matplotlib support"))
        matplotlib_box = newcb(_("Activate support"), 'pylab')
        autoload_matplotlib_box = newcb(
            _("Automatically import NumPy and Matplotlib modules"),
            'pylab/autoload',
            tip=_(
                "This is a convinience to use NumPy and Matplotlib\n"
                "in the console without explicitly importing the modules."
            )
        )
        autoload_matplotlib_box.setEnabled(self.get_option('pylab'))
        matplotlib_box.checkbox.toggled.connect(
            autoload_matplotlib_box.setEnabled
        )

        matplotlib_layout = QVBoxLayout()
        matplotlib_layout.addWidget(matplotlib_box)
        matplotlib_layout.addWidget(autoload_matplotlib_box)
        matplotlib_group.setLayout(matplotlib_layout)

        # Graphics backend group
        inline = _("Inline")
        automatic = _("Automatic")
        backend_group = QGroupBox(_("Graphics backend"))
        backend_label = QLabel(_("Choose how figures are displayed"))

        backends = [
            (inline, 'inline'),
            (automatic, 'auto'),
            ("Qt", 'qt'),
            ("Tk", 'tk'),
        ]

        if sys.platform == 'darwin':
            backends.append(("macOS", 'osx'))
        backends = tuple(backends)

        backend_box = self.create_combobox(
            _("Backend:"),
            backends,
            'pylab/backend',
            default='inline',
            tip=_(
                "If unsure, select {inline} to show figures in the Plots pane"
                "\nor {auto} to interact with them (zoom and pan) "
                "in a new window."
            ).format(inline=inline, auto=automatic),
        )

        backend_layout = QVBoxLayout()
        backend_layout.addWidget(backend_label)
        backend_layout.addWidget(backend_box)
        backend_group.setLayout(backend_layout)
        backend_group.setEnabled(self.get_option('pylab'))
        matplotlib_box.checkbox.toggled.connect(backend_group.setEnabled)

        # Inline backend group
        inline_group = QGroupBox(_("Inline backend"))
        inline_label = QLabel(_("Settings for figures in the Plots pane"))
        inline_label.setWordWrap(True)
        formats = (("PNG", 'png'), ("SVG", 'svg'))
        format_box = self.create_combobox(
            _("Format:") + "   ",
            formats,
            'pylab/inline/figure_format',
            default='png',
            tip=_(
                "PNG is more widely supported, "
                "while SVG is resolution-independent and easier to edit "
                "but complex plots may not be displayed correctly."
            ),
        )
        resolution_spin = self.create_spinbox(
            _("Resolution:") + "  ",
            " " + _("DPI"),
            'pylab/inline/resolution',
            min_=50,
            max_=999,
            step=0.1,
            tip=_("Only used when the format is PNG. Default is 144."),
        )
        width_spin = self.create_spinbox(
            _("Width:") + "  ",
            " " + _("inches"),
            'pylab/inline/width',
            min_=2,
            max_=20,
            step=1,
            tip=_("Default is 6"),
        )
        height_spin = self.create_spinbox(
            _("Height:") + "  ",
            " " + _("inches"),
            'pylab/inline/height',
            min_=1,
            max_=20,
            step=1,
            tip=_("Default is 4"),
        )
        fontsize_spin = self.create_spinbox(
            _("Font size:") + "  ",
            " " + _("points"),
            'pylab/inline/fontsize',
            min_=5,
            max_=48,
            step=1.0,
            tip=_("Default is 10"),
        )
        bottom_spin = self.create_spinbox(
            _("Bottom edge:") + "  ",
            " " + _("of figure height"),
            'pylab/inline/bottom',
            min_=0,
            max_=0.3,
            step=0.01,
            tip=_("The position of the bottom edge of the subplots,\n"
                  "as a fraction of the figure height (default is 0.11).")
        )
        bottom_spin.spinbox.setDecimals(2)
        bbox_inches_box = newcb(
            _("Use a tight layout for inline plots"),
            'pylab/inline/bbox_inches',
            tip=_("Sets 'bbox_inches' to 'tight' for inline plots.\n"
                  "When enabled, figures displayed in the Plots pane\n"
                  "may look different from those output with 'savefig'."))

        inline_v_layout = QVBoxLayout()
        inline_v_layout.addWidget(inline_label)
        inline_layout = QGridLayout()
        inline_layout.addWidget(format_box.label, 1, 0)
        inline_layout.addWidget(format_box.combobox, 1, 1)
        inline_layout.addWidget(format_box.help_label, 1, 3)

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
        matplotlib_box.checkbox.toggled.connect(inline_group.setEnabled)

        # --- Startup ---
        # Run lines group
        run_lines_group = QGroupBox(_("Run code"))
        run_lines_label = QLabel(_(
            "Enter a code snippet to run when a new console is started.\n"
            "Separate multiple lines by semicolons, for example:<br>"
            "<tt>import os; import sys</tt>"
        ))
        run_lines_label.setWordWrap(True)
        run_lines_edit = self.create_lineedit(_("Lines:"), 'startup/run_lines',
                                              '', alignment=Qt.Horizontal)

        run_lines_layout = QVBoxLayout()
        run_lines_layout.addWidget(run_lines_label)
        run_lines_layout.addWidget(run_lines_edit)
        run_lines_group.setLayout(run_lines_layout)

        # Run file group
        run_file_group = QGroupBox(_("Run a file"))
        run_file_label = QLabel(_(
            "Specify a Python file to execute at startup, similar to "
            "<tt>PYTHONSTARTUP</tt>"
        ))
        run_file_label.setWordWrap(True)
        file_radio = newcb(
            _("Execute the following file:"), 'startup/use_run_file', False
        )
        run_file_browser = self.create_browsefile('', 'startup/run_file', '')
        run_file_browser.setEnabled(False)
        file_radio.checkbox.toggled.connect(run_file_browser.setEnabled)

        run_file_layout = QVBoxLayout()
        run_file_layout.addWidget(run_file_label)
        run_file_layout.addWidget(file_radio)
        run_file_layout.addWidget(run_file_browser)
        run_file_group.setLayout(run_file_layout)

        # ---- Advanced settings ----
        # Autocall group
        autocall_group = QGroupBox(_("Autocall"))
        autocall_label = QLabel(_(
            "Implictly insert parethesis after any callable object, "
            "treating anything following it as arguments.<br>"
            "For example, typing <tt>print 'Number:', 42</tt> will execute "
            "<tt>print('Number:', 42)</tt>."
        ))
        autocall_label.setWordWrap(True)

        smart = _('Smart')
        full = _('Full')
        autocall_opts = ((_('Off'), 0), (smart, 1), (full, 2))
        autocall_box = self.create_combobox(
            _("Autocall:  "),
            autocall_opts,
            'autocall',
            default=0,
            tip=_(
                "In {smart} mode, Autocall is not applied if there are no "
                "arguments after the callable.\n"
                "In {full} mode, callable objects are called even if no "
                "arguments are present."
            ).format(smart=smart, full=full),
        )

        autocall_layout = QVBoxLayout()
        autocall_layout.addWidget(autocall_label)
        autocall_layout.addWidget(autocall_box)
        autocall_group.setLayout(autocall_layout)

        # Autoreload group
        autoreload_group = QGroupBox(_("Autoreload"))
        autoreload_label = QLabel(_(
            "Reload imported modules automatically before running code. "
            "This is a different mechanism than the User Module Reloader"
            "and can be slow on Windows due to limitations of its file system."
        ))
        autoreload_label.setWordWrap(True)

        autoreload_box = newcb(
            _("Use autoreload"),
            "autoreload",
            tip=_(
                "Enables the autoreload magic. Refer to its documentation to "
                "learn how to use it."
            )
        )

        autoreload_layout = QVBoxLayout()
        autoreload_layout.addWidget(autoreload_label)
        autoreload_layout.addWidget(autoreload_box)
        autoreload_group.setLayout(autoreload_layout)

        # Prompts group
        prompts_group = QGroupBox(_("Prompts"))
        prompts_label = QLabel(_(
            "Modify how input and output prompts are shown in the console."
        ))
        prompts_label.setWordWrap(True)
        in_prompt_edit = self.create_lineedit(
            _("Input prompt:"),
            'in_prompt',
            "",
            _('Default is<br>'
              '<tt>In [&lt;span class="in-prompt-number"&gt;%i&lt;/span&gt;]:</tt>'),
            alignment=Qt.Horizontal,
        )
        out_prompt_edit = self.create_lineedit(
            _("Output prompt:"),
            'out_prompt',
            "",
            _('Default is<br>'
              '<tt>Out[&lt;span class="out-prompt-number"&gt;%i&lt;/span&gt;]:</tt>'),
            alignment=Qt.Horizontal,
        )

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
              "generated by the subprocess module"),
            'hide_cmd_windows',
        )
        windows_layout = QVBoxLayout()
        windows_layout.addWidget(hide_cmd_windows)
        windows_group.setLayout(windows_layout)

        # --- Tabs organization ---
        self.create_tab(
            _("Interface"),
            [display_group, confirmations_group, comp_group, output_group]
        )

        self.create_tab(
            _("Plotting"),
            [matplotlib_group, backend_group, inline_group]
        )

        self.create_tab(
            _("Startup"),
            [run_lines_group, run_file_group]
        )

        self.create_tab(
            _("Advanced"),
            [autocall_group, autoreload_group, prompts_group, windows_group]
        )

    def warn_if_large_buffer(self):
        """Warn the user if the Console buffer size is very large."""
        if "buffer_size" not in self.changed_options:
            return

        msg = None
        buffer_size = self.buffer_spin.spinbox.value()

        # >10k line buffers can make Spyder slow, see spyder-ide/spyder#19091
        if buffer_size > 10_000:
            msg = _("Buffer sizes over 10000 lines can slow down Spyder")
        elif buffer_size == -1:
            msg = _("Unlimited buffer size can slow down Spyder severely")
        if msg:
            QMessageBox.warning(self, _("Warning"), msg, QMessageBox.Ok)
