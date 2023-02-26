import enum

from iterutil import chunks
from bitutil import bits_to_int, int_to_bits

class Hamming:
    DECODE = enum.Enum('DECODE', ['CORRECT', 'CORRECTED', 'UNCORRECTABLE'])

    def __init__(self, poly = (1, 0, 1, 1)):
        self.poly = poly
        self.taps = bits_to_int(poly)
        self.parity = len(poly) - 1
        self.bits = 2**self.parity - 1
        self.data = self.bits - self.parity
        self.mask = (1<<self.data) - 1
        self.high = 1 << (self.data - 1)

        self.syn_table = {}
        errpos = self.bits - 1
        syndrome = 1
        flag = False
        while errpos >= 0:
            if errpos == 0:
                errpos += self.bits
                flag = True
            self.syn_table[syndrome] = errpos
            if flag:
                break
            errpos -= 1
            syndrome = self.lfsr(syndrome)

    def __repr__(self):
        return f'<{type(self).__name__}({self.bits}, {self.data})>'

    def lfsr(self, reg):
        new = (reg<<1) & self.mask
        if self.high & new:
            new ^= self.taps
        return new

    def encode(self, bits):
        bits = list(bits)
        reg = 0
        for rnd in range(self.bits):
            #print('er', rnd, bin(reg))
            reg = self.lfsr(reg)
            if rnd < len(bits):
                reg ^= (1 if bits[rnd] else 0)
        #print('e', binstr(bits_to_int(bits), self.data), '->', binstr(reg & (self.high - 1), self.parity))
        yield from bits
        yield from int_to_bits(reg & (self.high - 1), self.parity)

    def decode(self, sym):
        sym = list(sym)
        reg = 0
        data = bits_to_int(sym[:self.data])
        for rnd in range(self.bits + self.parity):
            #print('dr', rnd, bin(reg))
            reg = self.lfsr(reg)
            if rnd < self.bits:
                reg ^= (1 if sym[rnd] else 0)
        #print('d', binstr(bits_to_int(sym), self.bits), binstr(data, self.data), binstr(bits_to_int(sym[self.data:]), self.parity), binstr(reg, 1 + self.parity))
        if reg == 0:
            return self.DECODE.CORRECT, sym[:self.data]
        errpos = self.syn_table.get(reg)
        #print('de', errpos)
        if errpos is None:
            return self.DECODE.UNCORRECTABLE, None
        errpos = self.bits - errpos
        if errpos < self.data:
            data ^= (1 << errpos)
        return self.DECODE.CORRECTED, int_to_bits(data, self.data)

    def encoder(self, bits, flatten=True):
        for win in chunks(bits, self.data):
            if flatten:
                yield from self.encode(win)
            else:
                yield tuple(self.encode(win))

    def decoder_success(self, bits):
        for win in chunks(bits, self.bits):
            yield self.decode(win)

    def decoder(self, bits, errors = True):
        for _, bits in self.decoder_success(bits):
            if bits is None:
                if errors:
                    yield bits
            else:
                yield from bits

if __name__ == '__main__':
    import random
    from modulate import bitwise_mod, differential_mod
    from bitutil import bitstring
    #bits = list(bitwise(b'Hello world'))
    bits = list(bitwise_mod(b'\x01\x23\x45\x67\x89\xab\xcd\xef'))
    print(bits)
    print(''.join(bitstring((differential_mod(bits)))))

    hm = Hamming()
    print(hm)
    print(hm.syn_table)
    enc = list(hm.encoder(bits))
    print(''.join(bitstring(enc)))
    for codeword in hm.encoder(bits, False):
        print('->', ''.join(bitstring(codeword)))
    print()
    for stat, sym in hm.decoder_success(enc):
        print('<-', stat, ''.join(bitstring(sym)) if sym is not None else None)
    dec = list(hm.decoder(enc))
    print(''.join(bitstring(dec)))
    print(dec == bits)
    for afflict in range(len(enc)):
        encerr = enc[:]
        print(afflict)
        encerr[afflict] = not encerr[afflict]
        decerr = list(hm.decoder(encerr))
        #print(''.join(bitstring(decerr)))
        print(decerr == bits)
        if decerr != bits:
            for stat, sym in hm.decoder_success(encerr):
                print('<-', stat, ''.join(bitstring(sym)) if sym is not None else None)
