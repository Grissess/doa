import math
import numpy as np

def sinc_diff(into, l, u, ti, te, samples):
    into.resize((samples,))
    t = np.linspace(ti, ti + te, samples)
    into[:] = (np.sin(t * u) - np.sin(t * l)) / t

class Symbols:
    NEXT = object()
    STOP = object()
    BITS = list(reversed([2**i for i in range(8)]))

    def __init__(self, bw = 4, samples = 256, tail = 2):
        self.samples = 256
        self.bw = bw
        self.tail = tail
        self.update()

    def update(self):
        self.syms = [
                np.ndarray((self.samples,)),
                np.ndarray((self.samples,)),
        ]
        sinc_diff(self.syms[0], 1, 1 + self.bw, -self.tail * math.tau, 2 * self.tail * math.tau, self.samples)
        sinc_diff(self.syms[1], 1 + self.bw, 1, -self.tail * math.tau, 2 * self.tail * math.tau, self.samples)
        self.sync_point = [
                int(self.samples * (1 - 1 / self.bw) / 2),
                int(self.samples * (1 + 1 / self.bw) / 2),
        ]

    def coder(self, initial_bit):
        # Startup: send the entire lead-in
        index = 0
        sym = self.syms[initial_bit]
        while True:
            yield sym[index]
            index += 1
            if index >= self.sync_point[1]:
                code = (yield Symbols.NEXT)
                if code is Symbols.STOP:
                    break
                index = self.sync_point[0]
                sym = self.syms[code]
        # Shutdown: trail out all the remaining symbols
        while index < len(sym):
            yield sym[index]
            index += 1

    def encode(self, by):
        coder = None
        for bt in by:
            bits = [1 if bit & bt != 0 else 0 for bit in Symbols.BITS]
            for bit in bits:
                if coder is None:
                    coder = self.coder(bit)
                else:
                    coder.send(bit)
                for samp in coder:
                    if samp is Symbols.NEXT:
                        break
                    yield samp
        coder.send(Symbols.STOP)
        yield from coder
