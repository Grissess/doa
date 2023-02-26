import numpy as np
import sys

from bitutil import bits_to_int, int_to_bits
from modulate import bpsk_mod, bitstuff_demod, bitstuff_mod, differential_demod, differential_mod

def sync_detect(samples, seq, threshold, with_level=False):
    seq = np.array(list(bpsk_mod(seq)))
    buffer = np.zeros_like(seq)
    index = 0
    for sample in samples:
        buffer[index] = sample
        level = seq.dot(np.concatenate([buffer[index+1:], buffer[:index+1]]))
        if with_level:
            yield level >= threshold, level
        else:
            yield level >= threshold
        index = (index + 1) % len(buffer)

class BARKER:
    ELEVEN = np.array([True, True, True, False, False, False, True, False, False, True, False])

def frame_demod(demod, coder, sync, limit=1024, with_begin=False, sym_hook=None, len_hook=None):
    in_frame = False
    len_bits = [False] * 4
    len_bit_idx = 0
    len_acc = 0
    buffer = None
    index = 0
    counter = 0
    start = None
    decode_win = [False] * coder.bits
    decode_win_pos = 0
    decoded_queue = None
    errs = 0

    for sym, syn in zip(demod, sync):
        if in_frame:
            decode_win[decode_win_pos] = sym
            decode_win_pos += 1
            if decode_win_pos >= coder.bits:
                decode_win_pos = 0
                state, decoded_queue = coder.decode(decode_win)
                decoded_queue = list(decoded_queue)
                if sym_hook:
                    sym_hook(
                            sample=counter,
                            decode_win=decode_win,
                            state=state,
                            decoded_queue=decoded_queue,
                    )
                if state != coder.DECODE.CORRECT:
                    errs += 1
                if decoded_queue is not None:
                    if len_bit_idx < 4:
                        decoded_queue = differential_demod(decoded_queue)
                    for sym in decoded_queue:
                        if len_bit_idx < 4:
                            len_bits[len_bit_idx] = sym
                            len_bit_idx += 1
                            if len_bit_idx >= 4:
                                bottom = bits_to_int(len_bits)
                                #print('fd bits', hex(bottom))
                                len_acc |= bottom & 0x7
                                if bottom & 0x8:
                                    len_bit_idx = 0
                                    len_acc <<= 3
                                    #print('fd next', bin(len_acc))
                                    if len_hook:
                                        len_hook(
                                                sample=counter,
                                                done=False,
                                                length=len_acc,
                                                bottom=bottom,
                                        )
                                else:
                                    if len_hook:
                                        len_hook(
                                                sample=counter,
                                                done=True,
                                                length=len_acc,
                                                bottom=bottom,
                                        )
                                    if len_acc > limit:
                                        in_frame = False
                                        break
                                    buffer = [None] * len_acc
                                    index = 0
                                    if not buffer:
                                        in_frame = False
                                    #print('\nfd len', len(buffer), file=sys.stderr)
                        else:
                            #print('fill', len(buffer), index, file=sys.stderr)
                            buffer[index] = sym
                            index += 1
                            if index >= len(buffer):
                                yield start, buffer, errs
                                in_frame = False
                                break
        elif syn:
            in_frame = True
            len_bit_idx = 0
            len_acc = 0
            start = counter
            decode_win_pos = 0
            errs = 0
            if with_begin:
                yield start, None
        counter += 1

def frame_mod(syms, coder, sync_pat, pream=[True, False]*8):
    syms = list(syms)
    length = len(syms)
    #print('fm', length, file=sys.stderr)
    yield from pream
    yield from sync_pat
    #print('fm t', length, hex(length))
    accum = []
    while length > 0:
        bottom = length & 0x7
        accum.append(bottom)
        length >>= 3
    #print(accum)
    for ix, nib in enumerate(reversed(accum)):
        if ix != len(accum) - 1:
            nib |= 0x8
        #print('fm', hex(nib))
        yield from differential_mod(coder.encode(int_to_bits(nib, 4)))
    yield from coder.encoder(syms)

if __name__ == '__main__':
    import random
    import itertools
    import modulate
    import channel

    np.random.seed(0x1337)
    random.seed(0x777)

    seq = BARKER.ELEVEN
    coder = channel.Hamming()
    msgpos = {}

    if len(sys.argv) > 1:
        noise = np.fromfile(sys.argv[1], np.float32)
    else:
        noise = np.random.standard_normal((4096,))
        noise *= 0.1
        #indices = set()
        #for _ in range(3):
        #    ix = random.randrange(len(noise) - len(seq))
        #    indices.add(ix)
        #    noise[ix:ix+len(seq)] += seq

        #for ix, item in enumerate(sync_detect(noise, seq, len(seq)/2, with_level=True)):
        #    det, lev = item
        #    print(noise[ix], int(det), lev, int(ix in indices))

        msgs = (b'haha', b'lol', b'dragon')

        for msg in msgs:
            diff = modulate.bitstuff_mod(modulate.bitwise_mod(msg))
            frame = frame_mod(diff, coder, seq)
            samples = np.array(list(modulate.bpsk_mod(frame)))
            ix = random.randrange(len(noise) - len(samples))
            noise[ix:ix + len(samples)] += samples
            msgpos[ix] = msg

    symlog = {}
    def sym_hook(sample, decode_win, state, decoded_queue):
        symlog[sample] = (
                bits_to_int(decode_win),
                state,
                bits_to_int(decoded_queue) if decoded_queue is not None else None,
        )
    lenlog = {}
    def len_hook(sample, done, length, bottom):
        lenlog[sample] = (done, length, bottom)

    rxa, rxb = itertools.tee(noise)
    syncdet = sync_detect(rxa, seq, len(seq)/2)
    demod = modulate.bpsk_demod(rxb)
    for start, buffer, errs in frame_demod(demod, coder, syncdet, sym_hook=sym_hook, len_hook=len_hook):
        print('k', start, (len(buffer) + 12) * coder.bits // coder.data, bytes(modulate.bitwise_demod(modulate.bitstuff_demod(buffer))), errs)

    print('\n')

    for samp, item in zip(noise, sync_detect(noise, seq, len(seq)/2, with_level=True)):
        det, lev = item
        print(samp, lev, int(det))

    print('\n')
    for ix, msg in msgpos.items():
        print(ix, msg)

    print('\n')
    for ix, dm in symlog.items():
        enc, state, dec = dm
        dec = f'{dec:X}' if dec is not None else 'None'
        print(ix, f'{enc:X}:{state.name}:{dec}')
    
    print('\n')
    for ix, lm in lenlog.items():
        done, length, bottom = lm
        print(ix, f'{done!r}:{length:X}:{bottom:X}')
