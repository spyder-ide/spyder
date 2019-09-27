#!/usr/bin/env python
#
"""Test performance of BloomFilter at a set capacity and error rate."""
import sys
from pybloom import BloomFilter
import bitarray, math, time
from utils import range_fn


def main(capacity=100000, request_error_rate=0.1):
    f = BloomFilter(capacity=capacity, error_rate=request_error_rate)
    assert (capacity == f.capacity)
    start = time.time()
    for i in range_fn(0, f.capacity):
        f.add(i, skip_check=True)
    end = time.time()
    print("{:5.3f} seconds to add to capacity, {:10.2f} entries/second".format(
            end - start, f.capacity / (end - start)))
    oneBits = f.bitarray.count(True)
    zeroBits = f.bitarray.count(False)
    print("Number of 1 bits:", oneBits)
    print("Number of 0 bits:", zeroBits)
    print("Number of Filter Bits:", f.num_bits)
    print("Number of slices:", f.num_slices)
    print("Bits per slice:", f.bits_per_slice)
    print("------")
    print("Fraction of 1 bits at capacity: {:5.3f}".format(
            oneBits / float(f.num_bits)))
    # Look for false positives and measure the actual fp rate
    trials = f.capacity
    fp = 0
    start = time.time()
    for i in range_fn(f.capacity, f.capacity + trials + 1):
        if i in f:
            fp += 1
    end = time.time()
    print(("{:5.3f} seconds to check false positives, "
           "{:10.2f} checks/second".format(end - start, trials / (end - start))))
    print("Requested FP rate: {:2.4f}".format(request_error_rate))
    print("Experimental false positive rate: {:2.4f}".format(fp / float(trials)))
    # Compute theoretical fp max (Goel/Gupta)
    k = f.num_slices
    m = f.num_bits
    n = f.capacity
    fp_theory = math.pow((1 - math.exp(-k * (n + 0.5) / (m - 1))), k)
    print("Projected FP rate (Goel/Gupta): {:2.6f}".format(fp_theory))

if __name__ == '__main__':
    main()
