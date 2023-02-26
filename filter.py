import numpy as np
import math

from iterutil import chunks

class FIRFilter:
    def __init__(self, taps):
        self.taps = np.array(taps)

    @classmethod
    def raised_cos(cls, size, period, beta=0.35, scale=None):
        if scale is None:
            scale = period
        t = np.arange(-(size // 2), 1 + size // 2)
        return cls(scale/period * np.sinc(t/period) * \
                np.cos(np.pi * beta * t/period) / \
                (1 - (2 * beta * t/period)**2)
        )

    def run(self, samples, run_out=True):
        buffer = np.zeros_like(self.taps)
        ii = 0
        for sample in samples:
            buffer[ii] = sample
            yield self.taps.dot(np.concatenate([buffer[ii:], buffer[:ii]]))
            ii = (ii + 1) % len(self.taps)
        if run_out:
            for _ in range(len(self.taps) // 2):
                buffer[ii] = 0.0
                yield self.taps.dot(np.concatenate([buffer[ii:], buffer[:ii]]))
                ii = (ii + 1) % len(self.taps)

def scale(samples, factor):
    for sample in samples:
        yield factor*sample

def impulse_interp(samples, width):
    for sample in samples:
        yield sample
        for _ in range(width - 1):
            yield 0.0

def clock_recover(samples, period, rate=0.3, mu=0.0, epsilon=1e-3, with_mu=False):
    last_out = (0.0, 0.0)
    last_rail = (0.0, 0.0)
    for win in chunks(samples, period, overlap=1, runt=True):
        if len(win) < period+1:
            win = win[:]
            win.extend([0.0] * (period - len(win) + 1))
        mu_floor = int(mu)
        mu_frac = mu - mu_floor
        a = win[mu_floor]
        if mu_frac > epsilon:
            b = win[mu_floor+1]
            out = b*mu_frac + a*(1-mu_frac)
        else:
            out = a
        rail = int(out.real > 0) + 1j*int(out.imag > 0)
        x = (rail - last_rail[0]) * last_out[1].conjugate()
        y = (out - last_out[0]) * last_rail[1].conjugate()
        mu_adj = (y-x).real
        mu = (mu + rate*mu_adj) % period
        if math.isnan(mu):
            mu = 0.0
        if with_mu:
            yield out, mu
        else:
            yield out
        last_out = (last_out[1], out)
        last_rail = (last_rail[1], rail)

def frequency_follow(samples, alpha=0.132, beta=0.00932, phase=0.0, freq=0.0, with_freq=False):
    for sample in samples:
        out = sample * np.exp(-1j*phase)
        error = out.real * out.imag
        freq += beta * error
        phase = (phase + freq + alpha * error) % math.tau
        if with_freq:
            yield out, freq
        else:
            yield out

if __name__ == '__main__':
    import channel
    import modulate
    import sys

    period = 16
    bits = list(modulate.bitwise_mod(b'Why aren\'t there more dragon books?'))

    diffenc = modulate.bitstuff_mod(modulate.differential_mod(bits))
    mod = list(modulate.bpsk_mod(diffenc))
    sig = impulse_interp(mod, period)
    fil = FIRFilter.raised_cos(101, period)
    out = list(fil.run(sig))

    for v in out:
        print(v)

    aud = np.array(out)/2
    aud.astype(np.float32).tofile('sig.raw')

    print('\n')
    
    pad = len(fil.taps) // (2*period)

    for _ in range(pad):
        print(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    clipped = np.array(out[len(fil.taps) // 2:])
    offset = 2.5
    froff = clipped * np.exp(1j*math.tau*np.linspace(0.0, offset, len(clipped)))

    recov = list(clock_recover(froff, period, with_mu=True))
    final = list(frequency_follow((s[0] for s in recov), with_freq=True))
    for orig, clk, fin in zip(mod, recov, final):
        sampc, mu = clk
        sampf, fr = fin
        print(orig, sampc.real, sampc.imag, mu, sampf.real, sampf.imag, fr)

    print('\n')

    fbits = modulate.bpsk_demod(s[0] for s in final)
    forig = modulate.differential_demod(modulate.bitstuff_demod(fbits))
    fbytes = modulate.bitwise_demod(forig)

    for ix, bt in enumerate(fbytes):
        ch = ''
        if 0 <= bt < 256:
            ch = chr(bt)
        print(pad + 15 + 16*ix, bt, repr(ch))
