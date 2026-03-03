# %% sig
def test_fn(arg1: bool | None = None):
# %% body
    """Partial docstring.
    return True
# %% numpy
    """
    SUMMARY.

    Parameters
    ----------
    arg1 : bool | None, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    bool
        DESCRIPTION.
    """
# %% google
    """SUMMARY.

    Args:
        arg1 (bool | None, optional): DESCRIPTION. Defaults to None.

    Returns:
        bool: DESCRIPTION.
    """
# %% sphinx
    """SUMMARY.

    :param arg1: DESCRIPTION, defaults to None
    :type arg1: bool | None

    :rtype: bool
    :returns: DESCRIPTION
    """
