from bitutil import bits_to_int, int_to_bits
from iterutil import chunks

def bpsk_mod(bits):
    for bit in bits:
        if bit:
            yield 1.0
        else:
            yield -1.0

def bpsk_demod(samples):
    for sample in samples:
        yield sample.real >= 0.0

def differential_mod(samples, initial=False):
    last = initial
    for sample in samples:
        yield last != sample
        last = sample

def differential_demod(samples, initial=False):
    last = initial
    for sample in samples:
        if sample:
            last = not last
        yield last

def bitwise_mod(bytestr, big=True):
    for byte in bytestr:
        yield from int_to_bits(byte, big=big)

def bitwise_demod(bits, big=True):
    for byte in chunks(bits, 8):
        yield bits_to_int(byte, big=big)

def reals(samples):
    for sample in samples:
        yield sample.real

def manchester_mod(bits, parity=True):
    for bit in bits:
        yield from [bit == parity, bit != parity]

def manchester_demod(bits, parity=True):
    for bits in chunks(bits, 2):
        if bits[0] == bits[1]:
            yield None
        else:
            yield bits[0] == parity

def bitstuff_mod(bits, run=6):
    ctr = 0
    for bit in bits:
        if bit:
            ctr = 0
        else:
            ctr += 1
        yield bit
        if ctr >= run:
            yield True
            ctr = 0

def bitstuff_demod(bits, run=6):
    ctr = 0
    for bit in bits:
        if bit:
            cmp = ctr
            ctr = 0
            if cmp >= run:
                continue
        else:
            ctr += 1
        yield bit
