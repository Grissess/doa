import sys
import queue

def chunks(samples, window, overlap=0, runt=False):
    size = window + overlap
    result = [None] * size
    index = 0
    for sample in samples:
        result[index] = sample
        index += 1
        if index >= size:
            yield result
            if overlap:
                result[:overlap] = result[-overlap:]
            index = overlap
    if index != overlap:
        if runt:
            yield result[:index]
        else:
            print(f'WARN: runt chunk {index}/{size} ({window}+{overlap}): {result}', file=sys.stderr)

def coiter():
    q = queue.Queue()
    def out():
        while True:
            itr = q.get()
            yield from itr
    def in_(itr):
        q.put(itr)
    return in_, out
