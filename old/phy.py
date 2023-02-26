import math
import numpy as np

START = object()
NEXT = object()
STOP = object()
BITS = list(reversed([2**i for i in range(8)]))

class Hm74:
    GENERATOR = np.array([
        0b1101,
        0b1011,
        0b1000,
        0b0111,
        0b0100,
        0b0010,
        0b0001,
    ])
    CHECK = np.array([
        0b1010101,
        0b0110011,
        0b0001111,
    ])
    EXTRACT = np.array([
        0b0010000,
        0b0000100,
        0b0000010,
        0b0000001,
    ])
    POPCOUNT = np.array([bin(x).count('1') for x in range(128)])
    PARITY = 0b1101000

    @classmethod
    def binmm(cls, a, v):
        c = cls.POPCOUNT[a & v] % 2
        return (c << np.arange(len(c) - 1, -1, -1)).sum()

    def __init__(self):
        self.errors = 0

    def encoder(self):
        code = START
        while True:
            sym = (yield code)
            if sym is STOP:
                break
            code = self.binmm(self.GENERATOR, sym) ^ self.PARITY

    def decoder(self):
        sym = START
        while True:
            code = (yield sym)
            if code is STOP:
                break
            syndrome = self.binmm(self.CHECK, code ^ self.PARITY)
            if syndrome > 0:
                self.errors += 1
                code ^= (1 << (syndrome - 1))
            sym = self.binmm(self.EXTRACT, code)

class GDCR:
    def __init__(self, sps = 8):
        self.sps = sps

    def filter(self):
        mu = 0.0

class BPSK:
    def __init__(self, sps = 8):
        self.sps = sps  # Samples Per Symbol
        self.update()

    def update(self):
        self.period = np.zeros(self.sps)
        self.period[0] = 1.0
        self.syms = [self.period, -1.0 * self.period]

    def encoder(self):
        sym = (yield NEXT)
        while sym is not STOP:
            yield from self.syms[sym]
            sym = (yield NEXT)

    def encode(self, bs):
        coder = self.encoder()

        def pass_next_stop():
            for v in coder:
                if v is NEXT:
                    break
                yield v

        yield from pass_next_stop()

        for byte in bs:
            bits = [1 if bit & byte != 0 else 0 for bit in BITS]
            for bit in bits:
                coder.send(bit)
                yield from pass_next_stop()

class RCPS:
    def __init__(self, sps = 8, taps = 101, beta = 0.35):
        self.sps = sps
        self.taps = taps
        self.beta = beta
        self.update()

    def update(self):
        x = np.arange((-self.taps - 1) / 2, (self.taps + 1) / 2) / self.sps
        self.ir = np.sinc(x) * np.cos(np.pi * self.beta * x) / (1 - (2 * self.beta * x)**2)

    def filter(self):
        carryin, carryout = np.zeros(self.taps // 2), np.zeros(self.taps // 2)
