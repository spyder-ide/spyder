# %% sig
def test(
    arg1,
    arg2=True,
):
# %% doc
    """
    This is a multi line docstring.

    It is very long.
        Sub indent.

    Parameters
    ----------
    arg1 : str
        The first arg.
    arg2 : bool, optional
        The second arg. The default is True.

    Returns
    -------
    str
        The string value passed.
    bool
        The boolean value passed.

    Examples
    --------
    Examples.

    Raises
    ------
    ValueError
        If the wrong arg is passed.

    See also
    --------
    See also stuff.
    """
# %% body
    raise ValueError("This is an error.")
    return "spam", True
# %% numpy
    """
    This is a multi line docstring.

    It is very long.
        Sub indent.

    Parameters
    ----------
    arg1 : str
        The first arg.
    arg2 : bool, optional
        The second arg. The default is True.

    Returns
    -------
    str
        The string value passed.
    bool
        The boolean value passed.

    Raises
    ------
    ValueError
        If the wrong arg is passed.

    Examples
    --------
    Examples.

    See also
    --------
    See also stuff.
    """
# %% google
    """
    This is a multi line docstring.

    It is very long.
        Sub indent.

    Parameters
    ----------
    arg1 : str
        The first arg.
    arg2 : bool, optional
        The second arg. The default is True.

    Returns
    -------
    str
        The string value passed.
    bool
        The boolean value passed.

    Raises
    ------
    ValueError
        If the wrong arg is passed.

    Examples
    --------
    Examples.

    See also
    --------
    See also stuff.
    """
# %% sphinx
    """
    This is a multi line docstring.

    It is very long.
        Sub indent.

    Parameters
    ----------
    arg1 : str
        The first arg.
    arg2 : bool, optional
        The second arg. The default is True.

    Returns
    -------
    str
        The string value passed.
    bool
        The boolean value passed.

    Raises
    ------
    ValueError
        If the wrong arg is passed.

    Examples
    --------
    Examples.

    See also
    --------
    See also stuff.
    """
