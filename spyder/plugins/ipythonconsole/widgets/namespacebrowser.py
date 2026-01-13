# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handle communications between the IPython Console and
the Variable Explorer
"""

# Standard library imports
import logging
import os
from pickle import PicklingError, UnpicklingError
import sys

# Third-party imports
import cloudpickle
from packaging.version import parse
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from spyder_kernels.comms.commbase import CommError

# Local imports
from spyder.api.translations import _
from spyder.config.base import is_conda_based_app

# For logging
logger = logging.getLogger(__name__)

# Max time before giving up when making a blocking call to the kernel
CALL_KERNEL_TIMEOUT = 30

# URLs
GH_ISSUES = "https://github.com/spyder-ide/spyder/issues/new"
VAREXP_DONATIONS = (
    "https://www.spyder-ide.org/donate/variable-explorer-improvements"
)
PROJECTS_DOC_PAGE = "https://docs.spyder-ide.org/current/panes/projects.html"


class NamepaceBrowserWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle communications
    between the IPython Console and the kernel namespace
    """
    # --- Public API --------------------------------------------------
    def get_value(self, name):
        """Ask kernel for a value"""
        # ---- Reasons
        reason_big = _("The variable is too big to be retrieved")
        reason_not_picklable = _(
            "It was not possible to create a copy of the variable in the "
            "kernel or to load that copy in Spyder.<br><br>"
            "If the object you're trying to view contains a generator, you "
            "need to replace it by a list because generators can't be "
            "serialized."
        )
        reason_dead = _("The kernel is dead")
        reason_other = _("An unknown error occurred, sorry.")
        reason_comm = _(
            "The channel used to communicate with the kernel is not working."
        )
        reason_missing_package_target = _(
            "The '<tt>{}</tt>' module is required to open this variable and "
            "it's not installed in the console environment. To fix this "
            "problem, please install it in the environment which you use to "
            "run your code."
        )
        reason_missing_package_installer = _(
            "The '<tt>{}</tt>' module is required to open this variable. "
            "Unfortunately, it's not part of our installer, which means your "
            "variable can't be displayed by Spyder."
        )
        reason_missing_package = _(
            "The '<tt>{}</tt>' module is required to open this variable and "
            "it's not installed alongside Spyder. To fix this problem, please "
            "install it in the same environment that you use to run Spyder."
        )
        reason_mismatched_numpy = _(
            "There is a mismatch between the Numpy versions used by Spyder "
            "and the kernel of your current console. To fix this problem, "
            "please upgrade <tt>numpy</tt> in the environment that you use to "
            "run Spyder to version 1.26.1 or higher."
        )
        reason_mismatched_pandas = _(
            "There is a mismatch between the Pandas versions used by Spyder "
            "and the kernel of your current console. To fix this problem, "
            "please upgrade <tt>pandas</tt> in the console environment "
            "to version 2.0 or higher."
        )
        reason_mismatched_python_installer = _(
            "There is a mismatch between the Python versions used by Spyder "
            "({}) and the kernel of your current console ({}).<br><br>"
            "To fix it, you need to recreate your console environment with "
            "Python {} or {}."
        )
        reason_mismatched_python = _(
            "There is a mismatch between the Python versions used by Spyder "
            "({}) and the kernel of your current console ({}).<br><br>"
            "To fix it, you need to either install Spyder in an environment "
            "with Python {} or {}, or recreate your console environment with "
            "Python {} or {}."
        )

        # ---- Notes
        missing_package_note_1 = _(
            "If you want to see this fixed in the future, please make a "
            "donation <a href='{}'>here</a>."
        ).format(VAREXP_DONATIONS)

        # This is necessary to inform users what they need to do to explore
        # their own objects.
        # See spyder-ide/spyder#15988
        missing_package_note_2 = _(
            "If the required module is yours, you need to create a "
            "<a href='{}'>Spyder project</a> for it or add the path where "
            "it's located to the PYTHONPATH manager (available in the "
            "<tt>Tools</tt> menu)."
        ).format(PROJECTS_DOC_PAGE)

        # ---- Final message
        msg = _(
            "<br>%s<br><br>"
            "<b>Note</b>: If you consider this to be a valid error that needs "
            "to be fixed by the Spyder team, please report it on "
            "<a href='{}'>Github</a>."
        ).format(GH_ISSUES)
        msg_without_note = "<br>%s"

        # ---- Raise error which includes the message
        kernel_call_success = False
        show_full_msg = True
        try:
            value = self.call_kernel(
                blocking=True,
                # We prefer not to display errors because it's not clear that
                # they are related to what users are doing in the Variable
                # Explorer. So, it's not user friendly.
                # See spyder-ide/spyder#22411
                display_error=False,
                timeout=CALL_KERNEL_TIMEOUT
            ).get_value(name, encoded=True)
            kernel_call_success = True
            value = cloudpickle.loads(value)
            return value
        except TimeoutError:
            raise ValueError(msg % reason_big)
        except (PicklingError, UnpicklingError, TypeError) as err:
            if str(err).startswith(
                ("code expected at most", "code() argument")
            ):
                # This error happens when Spyder is using Python 3.11+ and the
                # kernel 3.10-, or the other way around. In that case,
                # cloudpickle can't deserialize the objects sent from the
                # kernel and we need to inform users about it.
                # Fixes spyder-ide/spyder#24125.
                # Fixes spyder-ide/spyder#24950.
                py_spyder_version = ".".join(
                    [str(n) for n in sys.version_info[:3]]
                )
                py_kernel_version = self.get_pythonenv_info()["python_version"]

                if parse(py_spyder_version) < parse(py_kernel_version):
                    (
                        py_spyder_good_version,
                        py_spyder_compatible_versions,
                        py_kernel_good_version,
                        py_kernel_compatible_versions,
                    ) = (
                        "3.11",
                        _("greater"),
                        "3.10",
                        _("lower"),
                    )
                else:
                    (
                        py_spyder_good_version,
                        py_spyder_compatible_versions,
                        py_kernel_good_version,
                        py_kernel_compatible_versions,
                    ) = (
                        "3.10",
                        _("lower"),
                        "3.11",
                        _("greater"),
                    )

                if is_conda_based_app():
                    raise ValueError(
                        msg
                        % reason_mismatched_python_installer.format(
                            py_spyder_version,
                            py_kernel_version,
                            py_kernel_good_version,
                            py_kernel_compatible_versions,
                        )
                    )
                else:
                    raise ValueError(
                        msg
                        % reason_mismatched_python.format(
                            py_spyder_version,
                            py_kernel_version,
                            py_spyder_good_version,
                            py_spyder_compatible_versions,
                            py_kernel_good_version,
                            py_kernel_compatible_versions,
                        )
                    )

            raise ValueError(msg % reason_not_picklable)
        except RuntimeError:
            raise ValueError(msg % reason_dead)
        except KeyError:
            raise
        except CommError:
            raise ValueError(msg % reason_comm)
        except ModuleNotFoundError as e:
            if not kernel_call_success:
                name = e.args[0].error.name
                reason = reason_missing_package_target.format(name)
            elif e.name.startswith('numpy._core') and not is_conda_based_app():
                reason = reason_mismatched_numpy
            elif e.name == 'pandas.core.indexes.numeric':
                reason = reason_mismatched_pandas
            else:
                # We don't show the full message in this case so people don't
                # report this problem to Github and instead encourage them to
                # donate to the project that will solve the problem.
                # See spyder-ide/spyder#24922 for the details.
                show_full_msg = False

                if is_conda_based_app():
                    opening_paragraph = reason_missing_package_installer
                else:
                    opening_paragraph = reason_missing_package

                notes_vmargin = "0.4em" if os.name == "nt" else "0.3em"
                notes = (
                    "<style>"
                    "ul, li {{margin-left: -15px}}"
                    "li {{margin-bottom: {}}}"
                    "</style>"
                    "<ul>"
                    "<li>{}</li>"
                    "<li>{}</li>"
                    "</ul>"
                ).format(
                    notes_vmargin,
                    missing_package_note_1,
                    missing_package_note_2,
                )

                reason = (
                    opening_paragraph.format(e.name)
                    + "<br><br>"
                    + _("<b>Notes</b>:")
                    + notes
                )

            if show_full_msg:
                raise ValueError(msg % reason)
            else:
                raise ValueError(msg_without_note % reason)
        except Exception:
            raise ValueError(msg % reason_other)

    def set_value(self, name, value):
        """Set value for a variable"""
        reason_mismatched_numpy = _(
            "There is a mismatch between the Numpy versions used by Spyder "
            "and the kernel of your current console. To fix this problem, "
            "please upgrade <tt>numpy</tt> in the console environment to "
            "version 2.0 or higher."
        )
        msg = _(
            "<br>%s<br><br>"
            "<b>Note</b>: If you consider this to be a valid error that needs "
            "to be fixed by the Spyder team, please report it on "
            "<a href='{}'>Github</a>."
        ).format(GH_ISSUES)

        # Encode with cloudpickle and base64
        encoded_value = cloudpickle.dumps(value)

        try:
            self.call_kernel(
                interrupt=True,
                blocking=True,
                display_error=True,
            ).set_value(name, encoded_value, encoded=True)
        except ModuleNotFoundError as e:
            name = e.args[0].error.name
            if name.startswith('numpy._core'):
                raise ValueError(msg % reason_mismatched_numpy)
        except Exception:
            pass  # swallow exception

    def remove_value(self, name):
        """Remove a variable"""
        self.call_kernel(
            interrupt=True,
            blocking=False,
            display_error=True,
            ).remove_value(name)

    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        self.call_kernel(
            interrupt=True,
            blocking=False,
            display_error=True,
            ).copy_value(orig_name, new_name)
