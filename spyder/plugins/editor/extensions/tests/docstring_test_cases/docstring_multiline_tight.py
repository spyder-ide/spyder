# %% sig
def test(
    arg1,
    arg2=True,
):
# %% doc
    """This is a multi line docstring.

    It is very long.
        Sub indent."""
# %% body
    return "foo"
# %% numpy
    """
    This is a multi line docstring.

    It is very long.
        Sub indent.

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
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    Args:
        arg1 (TYPE): DESCRIPTION.
        arg2 (TYPE, optional): DESCRIPTION. Defaults to True.

    Returns:
        str: DESCRIPTION.
    """
# %% sphinx
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    :param arg1: DESCRIPTION
    :type arg1: TYPE
    :param arg2: DESCRIPTION, defaults to True
    :type arg2: TYPE

    :rtype: str
    :returns: DESCRIPTION
    """
