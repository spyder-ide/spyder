# %% sig
def get_action(
    self, widget_id
) -> spyder.utils.qthelpers.SpyderAction | None:
# %% body
    if widget_id in self._widgets:
        return self._widgets[widget_id][1]
    return None
# %% numpy
    """
    SUMMARY.

    Parameters
    ----------
    widget_id : TYPE
        DESCRIPTION.

    Returns
    -------
    spyder.utils.qthelpers.SpyderAction | None
        DESCRIPTION.
    """
# %% google
    """SUMMARY.

    Args:
        widget_id (TYPE): DESCRIPTION.

    Returns:
        spyder.utils.qthelpers.SpyderAction | None: DESCRIPTION.
    """
# %% sphinx
    """SUMMARY.

    :param widget_id: DESCRIPTION
    :type widget_id: TYPE

    :rtype: spyder.utils.qthelpers.SpyderAction | None
    :returns: DESCRIPTION
    """
