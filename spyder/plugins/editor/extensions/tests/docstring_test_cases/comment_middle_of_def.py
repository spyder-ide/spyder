# %% sig
  def test(v1: str = "#", # comment, with '#' and "#"
           v2: str = '#') -> str:
# %% numpy
      """
      SUMMARY.

      Parameters
      ----------
      v1 : str, optional
          DESCRIPTION. The default is "#".
      v2 : str, optional
          DESCRIPTION. The default is '#'.

      Returns
      -------
      str
          DESCRIPTION.
      """
# %% google
      """SUMMARY.

      Args:
          v1 (str, optional): DESCRIPTION. Defaults to "#".
          v2 (str, optional): DESCRIPTION. Defaults to '#'.

      Returns:
          str: DESCRIPTION.
      """
# %% sphinx
      """SUMMARY.

      :param v1: DESCRIPTION, defaults to "#"
      :type v1: str, optional
      :param v2: DESCRIPTION, defaults to '#'
      :type v2: str, optional
      :return: DESCRIPTION
      :rtype: str
      """
