from math import cos
from numpy import (
   linspace)

from subdir.a import (
    bar)

# We shouldn't show symbols for relative imports in the Outline.
# This is a regression test for issue spyder-ide/spyder#16352.
from ..a import (
    MyOtherClass)

from ...file2 import (
    MyClass,
    foo
)

def baz(x):
    return x

class AnotherClass:
    E = 1

    def five(self):
        return 5

    def six(self):
        return 4
