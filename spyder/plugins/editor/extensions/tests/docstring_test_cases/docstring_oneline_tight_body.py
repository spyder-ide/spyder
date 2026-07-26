# %% sig
def test(
    arg1,
    arg2=True,
):
# %% doc
    """This is a test docstring."""
# %% body
    return "foo"
# %% numpy
    """
    This is a test docstring.

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
    """This is a test docstring.

    Args:
        arg1 (TYPE): DESCRIPTION.
        arg2 (TYPE, optional): DESCRIPTION. Defaults to True.

    Returns:
        str: DESCRIPTION.
    """
# %% sphinx
    """This is a test docstring.

    :param arg1: DESCRIPTION
    :type arg1: TYPE
    :param arg2: DESCRIPTION, defaults to True
    :type arg2: TYPE

    :rtype: str
    :returns: DESCRIPTION
    """
