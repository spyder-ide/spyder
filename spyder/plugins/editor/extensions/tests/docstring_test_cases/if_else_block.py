# %% sig
    def foo():
# %% body
        if 1:
            raise ValueError
        else:
            return
# %% post
class F:
# %% numpy
        """
        SUMMARY.

        Returns
        -------
        None.

        Raises
        ------
        ValueError
            DESCRIPTION.
        """
# %% google
        """SUMMARY.

        Returns:
            None.

        Raises:
            ValueError: DESCRIPTION.
        """
# %% sphinx
        """SUMMARY.

        :raises ValueError: DESCRIPTION
        :return: DESCRIPTION
        :rtype: TYPE
        """
