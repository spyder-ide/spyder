# %% sig
def test_fn(arg1: bool | None = None):
# %% doc
    """A docstring."""
# %% body
    (return True
# %% numpy
    """
    A docstring.

    Parameters
    ----------
    arg1 : bool | None, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    None
    """
# %% google
    """A docstring.

    Args:
        arg1 (bool | None, optional): DESCRIPTION. Defaults to None.

    Returns:
        None
    """
# %% sphinx
    """A docstring.

    :param arg1: DESCRIPTION, defaults to None
    :type arg1: bool | None

    :rtype: None
    """
