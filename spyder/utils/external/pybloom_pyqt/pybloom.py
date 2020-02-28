"""This module implements a bloom filter probabilistic data structure and
an a Scalable Bloom Filter that grows in size as your add more items to it
without increasing the false positive error_rate.

Requires the bitarray library: http://pypi.python.org/pypi/bitarray/
"""
from __future__ import absolute_import
import math
import hashlib
from .utils import range_fn, is_string_io, running_python_3
from struct import unpack, pack, calcsize

try:
    from PyQt5.QtCore import QBitArray, QFile, QDataStream, QIODevice
except ImportError:
    raise ImportError('pybloom_pyqt requires QtCore.QBitArray')


def make_hashfuncs(num_slices, num_bits):
    if num_bits >= (1 << 31):
        fmt_code, chunk_size = 'Q', 8
    elif num_bits >= (1 << 15):
        fmt_code, chunk_size = 'I', 4
    else:
        fmt_code, chunk_size = 'H', 2
    total_hash_bits = 8 * num_slices * chunk_size
    if total_hash_bits > 384:
        hashfn = hashlib.sha512
    elif total_hash_bits > 256:
        hashfn = hashlib.sha384
    elif total_hash_bits > 160:
        hashfn = hashlib.sha256
    elif total_hash_bits > 128:
        hashfn = hashlib.sha1
    else:
        hashfn = hashlib.md5

    fmt = fmt_code * (hashfn().digest_size // chunk_size)
    num_salts, extra = divmod(num_slices, len(fmt))
    if extra:
        num_salts += 1
    salts = tuple(hashfn(hashfn(pack('I', i)).digest())
                  for i in range_fn(0, num_salts))

    def _hash_maker(key):
        if running_python_3:
            if isinstance(key, str):
                key = key.encode('utf-8')
            else:
                key = str(key).encode('utf-8')
        else:
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            else:
                key = str(key)
        i = 0
        for salt in salts:
            h = salt.copy()
            h.update(key)
            for uint in unpack(fmt, h.digest()):
                yield uint % num_bits
                i += 1
                if i >= num_slices:
                    return

    return _hash_maker, hashfn


class BloomFilter(object):
    FILE_FMT = b'<dQQQQ'

    def __init__(self, capacity, error_rate=0.001):
        """Implements a space-efficient probabilistic data structure

        capacity
            this BloomFilter must be able to store at least *capacity* elements
            while maintaining no more than *error_rate* chance of false
            positives
        error_rate
            the error_rate of the filter returning false positives. This
            determines the filters capacity. Inserting more than capacity
            elements greatly increases the chance of false positives.
        """
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")
        # given M = num_bits, k = num_slices, P = error_rate, n = capacity
        #       k = log2(1/P)
        # solving for m = bits_per_slice
        # n ~= M * ((ln(2) ** 2) / abs(ln(P)))
        # n ~= (k * m) * ((ln(2) ** 2) / abs(ln(P)))
        # m ~= n * abs(ln(P)) / (k * (ln(2) ** 2))
        num_slices = int(math.ceil(math.log(1.0 / error_rate, 2)))
        bits_per_slice = int(math.ceil(
            (capacity * abs(math.log(error_rate))) /
            (num_slices * (math.log(2) ** 2))))
        self._setup(error_rate, num_slices, bits_per_slice, capacity, 0)
        self.bitarray = QBitArray(self.num_bits)

    def _setup(self, error_rate, num_slices, bits_per_slice, capacity, count):
        self.error_rate = error_rate
        self.num_slices = num_slices
        self.bits_per_slice = bits_per_slice
        self.capacity = capacity
        self.num_bits = num_slices * bits_per_slice
        self.count = count
        self.make_hashes, self.hashfn = make_hashfuncs(self.num_slices,
                                                       self.bits_per_slice)

    def __contains__(self, key):
        """Tests a key's membership in this bloom filter.
        """
        bits_per_slice = self.bits_per_slice
        bitarray = self.bitarray
        hashes = self.make_hashes(key)
        offset = 0
        for k in hashes:
            if not bitarray[offset + k]:
                return False
            offset += bits_per_slice
        return True

    def __len__(self):
        """Return the number of keys stored by this bloom filter."""
        return self.count

    def add(self, key, skip_check=False):
        """ Adds a key to this bloom filter. If the key already exists in this
        filter it will return True. Otherwise False.
        """
        bitarray = self.bitarray
        bits_per_slice = self.bits_per_slice
        hashes = self.make_hashes(key)
        found_all_bits = True
        if self.count > self.capacity:
            raise IndexError("BloomFilter is at capacity")
        offset = 0
        for k in hashes:
            if not skip_check and found_all_bits and not bitarray[offset + k]:
                found_all_bits = False
            self.bitarray.setBit(offset + k)
            offset += bits_per_slice

        if skip_check:
            self.count += 1
            return False
        elif not found_all_bits:
            self.count += 1
            return False
        else:
            return True

    def copy(self):
        """Return a copy of this bloom filter.
        """
        new_filter = BloomFilter(self.capacity, self.error_rate)
        new_filter.bitarray = QBitArray(self.bitarray)
        return new_filter

    def union(self, other):
        """ Calculates the union of the two underlying bitarrays and returns
        a new bloom filter object."""
        if self.capacity != other.capacity or \
                self.error_rate != other.error_rate:
            raise ValueError("Unioning filters requires both filters to have "
                             "both the same capacity and error rate")
        new_bloom = self.copy()
        new_bloom.bitarray = new_bloom.bitarray | other.bitarray
        return new_bloom

    def __or__(self, other):
        return self.union(other)

    def intersection(self, other):
        """ Calculates the intersection of the two underlying bitarrays and
        returns a new bloom filter object."""
        if self.capacity != other.capacity or \
                self.error_rate != other.error_rate:
            raise ValueError("Intersecting filters requires both filters to "
                             "have equal capacity and error rate")
        new_bloom = self.copy()
        new_bloom.bitarray = new_bloom.bitarray & other.bitarray
        return new_bloom

    def __and__(self, other):
        return self.intersection(other)

    def tofile(self, path):
        """Write the bloom filter to file object `f'. Underlying bits
        are written as machine values. This is much more space
        efficient than pickling the object."""
        # f.write(pack(self.FILE_FMT, self.error_rate, self.num_slices,
        #              self.bits_per_slice, self.capacity, self.count))
        # f.write(self.bitarray.bits)
        f = QFile(path)
        if f.open(QIODevice.WriteOnly):
            out = QDataStream(f)
            out.writeBytes(self.FILE_FMT)
            out.writeFloat(self.error_rate)
            out.writeInt(self.num_slices)
            out.writeInt(self.bits_per_slice)
            out.writeInt(self.capacity)
            out.writeInt(self.count)
            out << self.bitarray
            f.flush()
            f.close()

    @classmethod
    def fromfile(cls, path):
        """Read a bloom filter from file-object `f' serialized with
        ``BloomFilter.tofile''. """
        f = QFile(path)
        if not f.open(QIODevice.ReadOnly):
            raise ValueError("unable to open file " + path)

        data = QDataStream(f)
        file_fmt = data.readBytes()
        if file_fmt != cls.FILE_FMT:
            raise ValueError('unexpected file format')

        error_rate = data.readFloat()
        num_slices = data.readInt()
        bits_per_slice = data.readInt()
        capacity = data.readInt()
        count = data.readInt()
        bitarray = QBitArray()

        filter = cls(1)  # Bogus instantiation, we will `_setup'.
        filter._setup(error_rate, num_slices, bits_per_slice, capacity, count)
        filter.bitarray = QBitArray()
        data >> filter.bitarray

        return filter

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['make_hashes']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.make_hashes, self.hashfn = make_hashfuncs(self.num_slices,
                                                       self.bits_per_slice)


class ScalableBloomFilter(object):
    SMALL_SET_GROWTH = 2  # slower, but takes up less memory
    LARGE_SET_GROWTH = 4  # faster, but takes up more memory faster
    FILE_FMT = '<idQd'

    def __init__(self, initial_capacity=100, error_rate=0.001,
                 mode=LARGE_SET_GROWTH):
        """Implements a space-efficient probabilistic data structure that
        grows as more items are added while maintaining a steady false
        positive rate

        initial_capacity
            the initial capacity of the filter
        error_rate
            the error_rate of the filter returning false positives. This
            determines the filters capacity. Going over capacity greatly
            increases the chance of false positives.
        mode
            can be either ScalableBloomFilter.SMALL_SET_GROWTH or
            ScalableBloomFilter.LARGE_SET_GROWTH. SMALL_SET_GROWTH is slower
            but uses less memory. LARGE_SET_GROWTH is faster but consumes
            memory faster.
        """
        if not error_rate or error_rate < 0:
            raise ValueError("Error_Rate must be a decimal less than 0.")
        self._setup(mode, 0.9, initial_capacity, error_rate)
        self.filters = []

    def _setup(self, mode, ratio, initial_capacity, error_rate):
        self.scale = mode
        self.ratio = ratio
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate

    def __contains__(self, key):
        """Tests a key's membership in this bloom filter.
        """
        for f in reversed(self.filters):
            if key in f:
                return True
        return False

    def add(self, key):
        """Adds a key to this bloom filter.
        If the key already exists in this filter it will return True.
        Otherwise False.
        """
        if key in self:
            return True
        if not self.filters:
            filter = BloomFilter(
                capacity=self.initial_capacity,
                error_rate=self.error_rate * self.ratio)
            self.filters.append(filter)
        else:
            filter = self.filters[-1]
            if filter.count >= filter.capacity:
                filter = BloomFilter(
                    capacity=filter.capacity * self.scale,
                    error_rate=filter.error_rate * self.ratio)
                self.filters.append(filter)
        filter.add(key, skip_check=True)
        return False

    def copy(self):
        """ Returns a clone of this instance.
        This is used instead of copy.deepcopy because QBitArray
        is not pickle-able (error can't pickle QBitArray objects) """
        cloned = ScalableBloomFilter(self.initial_capacity,
                                     self.error_rate,
                                     self.scale)
        for f in self.filters:
            cloned.filters.append(f.copy())
        return cloned

    def union(self, other):
        """ Calculates the union of the underlying classic bloom filters and
        returns a new scalable bloom filter object."""

        if self.scale != other.scale or \
                self.initial_capacity != other.initial_capacity or \
                self.error_rate != other.error_rate:
            raise ValueError("Unioning two scalable bloom filters requires "
                             "both filters to have both the same mode, "
                             "initial capacity and error rate")
        if len(self.filters) > len(other.filters):
            larger_sbf = self.copy()
            smaller_sbf = other
        else:
            larger_sbf = other.copy()
            smaller_sbf = self
        # Union the underlying classic bloom filters
        new_filters = []
        for i in range(len(smaller_sbf.filters)):
            new_filter = larger_sbf.filters[i] | smaller_sbf.filters[i]
            new_filters.append(new_filter)
        for i in range(len(smaller_sbf.filters), len(larger_sbf.filters)):
            new_filters.append(larger_sbf.filters[i])
        larger_sbf.filters = new_filters
        return larger_sbf

    def __or__(self, other):
        return self.union(other)

    @property
    def capacity(self):
        """Returns the total capacity for all filters in this SBF"""
        return sum(f.capacity for f in self.filters)

    @property
    def count(self):
        return len(self)

    def tofile(self, f):
        """Serialize this ScalableBloomFilter into the file-object
        `f'."""
        f.write(pack(self.FILE_FMT, self.scale, self.ratio,
                     self.initial_capacity, self.error_rate))

        # Write #-of-filters
        f.write(pack(b'<l', len(self.filters)))

        if len(self.filters) > 0:
            # Then each filter directly, with a header describing
            # their lengths.
            headerpos = f.tell()
            headerfmt = b'<' + b'Q' * (len(self.filters))
            f.write(b'.' * calcsize(headerfmt))
            filter_sizes = []
            for filter in self.filters:
                begin = f.tell()
                filter.tofile(f)
                filter_sizes.append(f.tell() - begin)

            f.seek(headerpos)
            f.write(pack(headerfmt, *filter_sizes))

    @classmethod
    def fromfile(cls, f):
        """Deserialize the ScalableBloomFilter in file object `f'."""
        filter = cls()
        filter._setup(*unpack(cls.FILE_FMT, f.read(calcsize(cls.FILE_FMT))))
        nfilters, = unpack(b'<l', f.read(calcsize(b'<l')))
        if nfilters > 0:
            header_fmt = b'<' + b'Q' * nfilters
            bytes = f.read(calcsize(header_fmt))
            filter_lengths = unpack(header_fmt, bytes)
            for fl in filter_lengths:
                filter.filters.append(BloomFilter.fromfile(f, fl))
        else:
            filter.filters = []

        return filter

    def __len__(self):
        """Returns the total number of elements stored in this SBF"""
        return sum(f.count for f in self.filters)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
