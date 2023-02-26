def bits_to_int(bits, big=True):
    src = reversed(bits) if big else bits
    return sum((1<<i) for i, b in enumerate(src) if b)

def int_to_bits(value, num=8, big=True):
    src = range(num)
    src = reversed(src) if big else src
    for bit in src:
        yield (1<<bit) & value > 0

def bitstring(bits):
    for b in bits:
        if b is True:
            yield '1'
        elif b is False:
            yield '0'
        elif b is None:
            yield 'X'
        else:
            yield '?'

def binstr(v, bits=8):
    return f'{v:0{bits}b}'
