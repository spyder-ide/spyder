#######################################################################
# Implements a topological sort algorithm.
#
# Copyright 2014 True Blade Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Notes:
#  Based on http://code.activestate.com/recipes/578272-topological-sort
#   with these major changes:
#    Added unittests.
#    Deleted doctests (maybe not the best idea in the world, but it cleans
#     up the docstring).
#    Moved functools import to the top of the file.
#    Changed assert to a ValueError.
#    Changed iter[items|keys] to [items|keys], for python 3
#     compatibility. I don't think it matters for python 2 these are
#     now lists instead of iterables.
#    Copy the input so as to leave it unmodified.
#    Renamed function from toposort2 to toposort.
#    Handle empty input.
#    Switch tests to use set literals.
#
########################################################################

from spyder.utils.external.toposort.toposort import (CircularDependencyError,
                                                     toposort,
                                                     toposort_flatten)
