# %% sig
def test_fn(arg1, arg2: bool = True) -> str:
# %% body
    raise ValueError
    if True:
        return "a", True
    else:
        return "B", False
# %% numpy
    """
    SUMMARY.

    Parameters
    ----------
    arg1 : TYPE
        DESCRIPTION.
    arg2 : bool, optional
        DESCRIPTION. The default is True.

    Returns
    -------
    str
        DESCRIPTION.

    Raises
    ------
    ValueError
        DESCRIPTION.
    """
# %% google
    """SUMMARY.

    Args:
        arg1 (TYPE): DESCRIPTION.
        arg2 (bool, optional): DESCRIPTION. Defaults to True.

    Returns:
        str: DESCRIPTION.

    Raises:
        ValueError: DESCRIPTION.
    """
# %% sphinx
    """SUMMARY.

    :param arg1: DESCRIPTION
    :type arg1: TYPE
    :param arg2: DESCRIPTION, defaults to True
    :type arg2: bool

    :rtype: str
    :returns: DESCRIPTION

    :raises ValueError: DESCRIPTION
    """
