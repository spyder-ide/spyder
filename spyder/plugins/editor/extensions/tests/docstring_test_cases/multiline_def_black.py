# %% sig
def test(
    arg1,
    arg2=True,
):
# %% body
    return "foo"
# %% numpy
    """
    SUMMARY.

    Parameters
    ----------
    arg1 : TYPE
        DESCRIPTION.
    arg2 : TYPE, optional
        DESCRIPTION. The default is True.

    Returns
    -------
    str
        DESCRIPTION.
    """
# %% google
    """SUMMARY.

    Args:
        arg1 (TYPE): DESCRIPTION.
        arg2 (TYPE, optional): DESCRIPTION. Defaults to True.

    Returns:
        str: DESCRIPTION.
    """
# %% sphinx
    """SUMMARY.

    :param arg1: DESCRIPTION
    :type arg1: TYPE
    :param arg2: DESCRIPTION, defaults to True
    :type arg2: TYPE

    :rtype: str
    :returns: DESCRIPTION
    """
