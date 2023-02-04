# Taken from the following comment:
# https://github.com/spyder-ide/spyder/issues/16406#issuecomment-917992317
#
# This helps to test a regression for issue spyder-ide/spyder#16406

import logging


def some_function():
    logging.info('Some message')


class SomeClass:
    def __init__(self):
        pass

    def some_method(self):
        pass
