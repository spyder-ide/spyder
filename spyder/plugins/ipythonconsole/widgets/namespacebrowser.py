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
from pickle import PicklingError, UnpicklingError
import cloudpickle

# Third-party imports
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from spyder_kernels.comms.commbase import CommError

# Local imports
from spyder.config.base import _, is_conda_based_app

# For logging
logger = logging.getLogger(__name__)

# Max time before giving up when making a blocking call to the kernel
CALL_KERNEL_TIMEOUT = 30


class NamepaceBrowserWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle communications
    between the IPython Console and the kernel namespace
    """
    # --- Public API --------------------------------------------------
    def get_value(self, name):
        """Ask kernel for a value"""
        reason_big = _("The variable is too big to be retrieved")
        reason_not_picklable = _("The variable is not picklable")
        reason_dead = _("The kernel is dead")
        reason_other = _("An unkown error occurred. Check the console because "
                         "its contents could have been printed there")
        reason_comm = _("The comm channel is not working")
        reason_missing_package_installer = _(
            "The '{}' package is required to open this variable. "
            "Unfortunately, it's not part of our installer, which means your "
            "variable can't be displayed by Spyder."
        )
        reason_missing_package = _(
            "The '{}' package is required to open this variable and it's not "
            "installed alongside Spyder. To fix this problem, please install "
            "it in the same environment that you use to run Spyder."
        )
        msg = _("<br><i>%s.</i><br><br><br>"
                "<b>Note</b>: Please don't report this problem on Github, "
                "there's nothing to do about it.")
        try:
            value = self.call_kernel(
                blocking=True,
                display_error=True,
                timeout=CALL_KERNEL_TIMEOUT
            ).get_value(name, encoded=True)
            value = cloudpickle.loads(value)
            return value
        except TimeoutError:
            raise ValueError(msg % reason_big)
        except (PicklingError, UnpicklingError, TypeError):
            raise ValueError(msg % reason_not_picklable)
        except RuntimeError:
            raise ValueError(msg % reason_dead)
        except KeyError:
            raise
        except CommError:
            raise ValueError(msg % reason_comm)
        except ModuleNotFoundError as e:
            if is_conda_based_app():
                raise ValueError(
                    msg % reason_missing_package_installer.format(e.name)
                )
            else:
                raise ValueError(
                    msg % reason_missing_package.format(e.name)
                )
        except Exception:
            raise ValueError(msg % reason_other)

    def set_value(self, name, value):
        """Set value for a variable"""
        # Encode with cloudpickle and base64
        encoded_value = cloudpickle.dumps(value)
        self.call_kernel(
            interrupt=True,
            blocking=False,
            display_error=True,
            ).set_value(name, encoded_value, encoded=True)

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
