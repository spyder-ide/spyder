# %% sig
def test(
    arg1: str,
    arg2: bool = True,
):
# %% doc
    """This is a multi line docstring.

    It is very long.
        Sub indent.

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
        arg1 (str): DESCRIPTION.
        arg2 (bool, optional): DESCRIPTION. Defaults to True.

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
        arg1 (str): DESCRIPTION.
        arg2 (bool, optional): DESCRIPTION. Defaults to True.

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
        arg1 (str): DESCRIPTION.
        arg2 (bool, optional): DESCRIPTION. Defaults to True.

    Returns:
        tuple[str, bool]: The string and boolean value passed.

    Raises:
        ValueError: If the wrong value is passed.

    Examples:
        An example.

    See Also:
        See also stuff.
    """
