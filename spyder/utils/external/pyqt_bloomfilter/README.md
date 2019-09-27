[![Build Status](https://travis-ci.org/joseph-fox/python-bloomfilter.svg?branch=master)](https://travis-ci.org/joseph-fox/python-bloomfilter)

# Python Bloom Filter
Note: *This is a fork, which makes use of PyQt's BitArray implementation instead of the originally used pypy bitarray.*

This Bloom Filter has its tightening ratio updated to 0.9, and this ration 
is consistently used throughout the `pybloom` module.
Choosing r around 0.8 - 0.9 will result in better average space usage for wide
range of growth, therefore the default value of model is set to 
LARGE_SET_GROWTH. This is a module that includes a Bloom Filter data structure 
along with an implementation of Scalable Bloom Filters as discussed in:

```
P. Almeida, C.Baquero, N. Preguiça, D. Hutchison, Scalable Bloom Filters, (GLOBECOM 2007), IEEE, 2007.
```
Bloom filters are great if you understand what amount of bits you need to set
aside early to store your entire set. Scalable Bloom Filters allow your bloom
filter bits to grow as a function of false positive probability and size.

A filter is "full" when at capacity: `M * ((ln 2 ^ 2) / abs(ln p))`, where M
is the number of bits and p is the false positive probability. When capacity
is reached a new filter is then created exponentially larger than the last
with a tighter probability of false positives and a larger number of hash
functions.

```python
    >>> import pybloom_pyqt
    >>> f = pybloom_pyqt.BloomFilter(capacity=1000, error_rate=0.001)
    >>> [f.add(x) for x in range(10)]
    [False, False, False, False, False, False, False, False, False, False]
    >>> all([(x in f) for x in range(10)])
    True
    >>> 10 in f
    False
    >>> 5 in f
    True
    >>> f = pybloom_pyqt.BloomFilter(capacity=1000, error_rate=0.001)
    >>> for i in xrange(0, f.capacity):
    ...     _ = f.add(i)
    >>> (1.0 - (len(f) / float(f.capacity))) <= f.error_rate + 2e-18
    True

    >>> sbf = pybloom_pyqt.ScalableBloomFilter(mode=pybloom_pyqt.ScalableBloomFilter.SMALL_SET_GROWTH)
    >>> count = 10000
    >>> for i in range(0, count):
            _ = sbf.add(i)

    >>> (1.0 - (len(sbf) / float(count))) <= sbf.error_rate + 2e-18
    True
    # len(sbf) may not equal the entire input length. 0.01% error is well
    # below the default 0.1% error threshold. As the capacity goes up, the
    # error will approach 0.1%.
```
# Development
We follow this [git branching model](http://nvie.com/posts/a-successful-git-branching-model/), 
please have a look at it.


# Installation instructions
If you are installing from an internet-connected computer (or virtual 
install), you can use the pip python package manager to download and install 
this package. Simply type `pip install pybloom-live` from a DOS command 
prompt (`cmd.exe`) or a linux shell (e.g. `bash` or `dash` on MacOS X as well 
as linux OSes including debian, slackware, redhat, enoch and arch).

If using Windows and you are installing onto an air-gapped computer or want 
the most up-to-date version from this repository, you can do the following:

1. Download the zip file by clicking on the green "Clone or Download" 
link followed by "Download Zip."

2. Extract all the contents of the the zip folder.

3. Open command prompt (``cmd.exe``) to the extracted folder.
    a. Find the extracted folder in Windows Explorer.
    b. From the parent folder level Shift+RightClick on the folder.
    c. Select "Open command window here".

4. Type `pip install .`.

Similar steps are possible under linux and MacOS X.

# Installation verification
Type `pip show pybloom-live` from a command prompt. Version should be 
2.2.0 as of 2016-12-11.
