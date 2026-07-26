# %% sig
def test(
    arg1,
    arg2=True,
):
# %% doc
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    Args:
        arg1 (str): The first arg.
        arg2 (bool, optional): The second arg. Defaults to True.

    Returns:
        tuple[str, bool]: The string and boolean value passed.

    Examples:
        An example.

    Raises:
        ValueError: If the wrong value is passed.

    See Also:
        See also stuff.
    """
# %% body
    raise ValueError("This is an error.")
    return "spam", True
# %% numpy
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    Args:
        arg1 (str): The first arg.
        arg2 (bool, optional): The second arg. Defaults to True.

    Returns:
        tuple[str, bool]: The string and boolean value passed.

    Raises:
        ValueError: If the wrong value is passed.

    Examples:
        An example.

    See Also:
        See also stuff.
    """
# %% google
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    Args:
        arg1 (str): The first arg.
        arg2 (bool, optional): The second arg. Defaults to True.

    Returns:
        tuple[str, bool]: The string and boolean value passed.

    Raises:
        ValueError: If the wrong value is passed.

    Examples:
        An example.

    See Also:
        See also stuff.
    """
# %% sphinx
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    Args:
        arg1 (str): The first arg.
        arg2 (bool, optional): The second arg. Defaults to True.

    Returns:
        tuple[str, bool]: The string and boolean value passed.

    Raises:
        ValueError: If the wrong value is passed.

    Examples:
        An example.

    See Also:
        See also stuff.
    """
