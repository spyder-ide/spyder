"""
    ********************* VerySimpleWebBrowser ************************

    This is a Very Simple Web Browser implemented over Qt and QtWebKit.

    author: Juan Manuel Garcia <jmg.utn@gmail.com> ~/home

    *******************************************************************
"""

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) / 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

quicksort([3, 6, 8, 10, 1, 2, 1])