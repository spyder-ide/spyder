# -*- coding: utf-8 -*-
"""
test for PR: #6380
"""
import pytest
class TestClass():
    TEXT_ALL_GOOD = '''
    # -*- coding: utf-8 -*-
    """
    Created on %(date-spyder)s

    Creator: %(username-spyder)s
    """
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''
    TEXT_BAD_IN_TRIQUOTE = '''
    # -*- coding: utf-8 -*-
    """
    Created on %(date-spyder)s

    Creator: %(its_bad)s
    """
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''
    TEXT_BAD_OUTSIDE = '''
    # -*- coding: utf-8 -*-
    """
    Created on %(date-spyder)s

    Creator: %(username-spyder)s
    """
    import logzero,logging
    f = '%(color)s[%(levelname)s][%(funcName)s|%(lineno)s] -> %(message)s%(end_color)s'
    cts_msg = logzero.setup_logger(level=logging.INFO,# change level here
                                   formatter=logzero.LogFormatter(fmt=f))
    LD = cts_msg.debug
    LI = cts_msg.info
    LE = cts_msg.error
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''
    TEXT_BAD_EVERYWHERE = '''
    # -*- coding: utf-8 -*-
    """
    Created on %(date-spyder)s

    Creator: %(its_bad)s
    """
    import logzero,logging
    f = '%(color)s[%(levelname)s][%(funcName)s|%(lineno)s] -> %(message)s%(end_color)s'
    cts_msg = logzero.setup_logger(level=logging.INFO,# change level here
                                   formatter=logzero.LogFormatter(fmt=f))
    LD = cts_msg.debug
    LI = cts_msg.info
    LE = cts_msg.error
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''

    def _render_linebyline(self, t, _VARS=None):
        t = t.split('\n')
        for i, line in enumerate(t):
            try:
                t[i] = line % _VARS
            except Exception:
                pass
        return '\n'.join(t)

    def new(self, text):
        import time

        VARS = {
            'date-spyder': time.strftime("%Y-%m"),
            'username-spyder': 'cts',
        }
        """
        cant use "os.getenv('USERNAME')" here in order to pass the
        autotest proceed by appveyor and travis-ci.
        """

        try:
            text = text % VARS
        except (KeyError, TypeError):
            text = self._render_linebyline(text, VARS)

        return text

    def test_all_good(self):
        """all placeholders are vaild."""
        """expecting full-replaced."""
        result = self.new(self.TEXT_ALL_GOOD)
        expected = '''
    # -*- coding: utf-8 -*-
    """
    Created on 2018-02

    Creator: cts
    """
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''
        assert result == expected

    def test_bad_in_triquote(self):
        """some placeholders in triquote are invaild."""
        """expecting good ones been replaced, bad ones get ignored"""
        result = self.new(self.TEXT_BAD_IN_TRIQUOTE)
        expected = '''
    # -*- coding: utf-8 -*-
    """
    Created on 2018-02

    Creator: %(its_bad)s
    """
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''
        assert result == expected

    def test_bad_outside(self):
        """some placeholders outside triquote section are invaild."""
        """expecting good ones been replaced, bad ones get ignored"""
        result = self.new(self.TEXT_BAD_OUTSIDE)
        expected = '''
    # -*- coding: utf-8 -*-
    """
    Created on 2018-02

    Creator: cts
    """
    import logzero,logging
    f = '%(color)s[%(levelname)s][%(funcName)s|%(lineno)s] -> %(message)s%(end_color)s'
    cts_msg = logzero.setup_logger(level=logging.INFO,# change level here
                                   formatter=logzero.LogFormatter(fmt=f))
    LD = cts_msg.debug
    LI = cts_msg.info
    LE = cts_msg.error
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''
        assert result == expected

    def test_bad_everywhere(self):
        """invaild placeholders are in both inside and outside of triquote section."""
        """expecting good ones been replaced, bad ones get ignored"""
        result = self.new(self.TEXT_BAD_EVERYWHERE)
        expected = '''
    # -*- coding: utf-8 -*-
    """
    Created on 2018-02

    Creator: %(its_bad)s
    """
    import logzero,logging
    f = '%(color)s[%(levelname)s][%(funcName)s|%(lineno)s] -> %(message)s%(end_color)s'
    cts_msg = logzero.setup_logger(level=logging.INFO,# change level here
                                   formatter=logzero.LogFormatter(fmt=f))
    LD = cts_msg.debug
    LI = cts_msg.info
    LE = cts_msg.error
    ### requirements
    ### TODO


    if __name__ == '__main__':

    '''
        assert result == expected
if __name__ == '__main__':
    pytest.main()
