# %% sig
  def foo():
# %% body
      raise
      foo_raise()
      raisefoo()
      raise ValueError
      is_yield()
      raise ValueError('tt')
      yieldfoo()
      	raise TypeError('tt')
      _yield
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
      TypeError
          DESCRIPTION.
      """
# %% google
      """SUMMARY.

      Returns:
          None.

      Raises:
          ValueError: DESCRIPTION.
          TypeError: DESCRIPTION.
      """
# %% sphinx
      """SUMMARY.

      :raises ValueError: DESCRIPTION
      :raises TypeError: DESCRIPTION
      :return: DESCRIPTION
      :rtype: TYPE
      """
