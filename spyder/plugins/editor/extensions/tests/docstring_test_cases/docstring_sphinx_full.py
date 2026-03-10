# %% sig
def test(
    arg1,
    arg2=True,
):
# %% doc
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    :param arg1: The first arg
    :type arg1: str
    :param arg2: The second arg, defaults to True
    :type arg2: bool

    Other content here.

    :rtype: tuple[str, bool]
    :returns: The string and boolean value passed.

    More content here.

    :raises ValueError: If the wrong value is passed.

    Some other content.
    """
# %% body
    raise ValueError("This is an error.")
    return "spam", True
# %% numpy
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    :param arg1: The first arg
    :type arg1: str
    :param arg2: The second arg, defaults to True
    :type arg2: bool

    :rtype: tuple[str, bool]
    :returns: The string and boolean value passed.

    :raises ValueError: If the wrong value is passed.

    Other content here.

    More content here.

    Some other content.
    """
# %% google
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    :param arg1: The first arg
    :type arg1: str
    :param arg2: The second arg, defaults to True
    :type arg2: bool

    :rtype: tuple[str, bool]
    :returns: The string and boolean value passed.

    :raises ValueError: If the wrong value is passed.

    Other content here.

    More content here.

    Some other content.
    """
# %% sphinx
    """This is a multi line docstring.

    It is very long.
        Sub indent.

    :param arg1: The first arg
    :type arg1: str
    :param arg2: The second arg, defaults to True
    :type arg2: bool

    :rtype: tuple[str, bool]
    :returns: The string and boolean value passed.

    :raises ValueError: If the wrong value is passed.

    Other content here.

    More content here.

    Some other content.
    """
