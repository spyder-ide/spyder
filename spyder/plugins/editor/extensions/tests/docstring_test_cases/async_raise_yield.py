# %% sig
async def foo():
# %% body
    raise
    raise ValueError
    raise ValueError("test")
    raise TypeError("test")
    yield value
# %% numpy
    """
    SUMMARY.

    Yields
    ------
    TYPE
        DESCRIPTION.

    Raises
    ------
    ValueError
        DESCRIPTION.
    TypeError
        DESCRIPTION.
    """
# %% google
    """SUMMARY.

    Yields:
        TYPE: DESCRIPTION.

    Raises:
        ValueError: DESCRIPTION.
        TypeError: DESCRIPTION.
    """
# %% sphinx
    """SUMMARY.

    :rtype: TYPE
    :returns: DESCRIPTION

    :raises ValueError: DESCRIPTION
    :raises TypeError: DESCRIPTION
    """
