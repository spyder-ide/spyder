# %% sig
def test_fn():
# %% body
    foo = "a"
    bar = "b"
    if True:
        return foo, bar
    else:
        return foo, False
# %% numpy
    """
    SUMMARY.

    Returns
    -------
    foo : TYPE
        DESCRIPTION.
    TYPE
        DESCRIPTION.
    """
# %% google
    """SUMMARY.

    Returns:
        tuple[TYPE, TYPE]: DESCRIPTION.
    """
# %% sphinx
    """SUMMARY.

    :rtype: tuple[TYPE, TYPE]
    :returns: DESCRIPTION
    """
