import asyncio
import threading
import queue
import itertools
import functools
import argparse

import pytun
import pyaudio
import numpy as np

import filter
import framing
import modulate
import channel
import iterutil

Queue = queue.SimpleQueue

def recv_into(ctx, bufsz=4096):
    pkt = ctx.tun.read(bufsz)
    print('i', len(pkt), pkt)
    ctx.enqueue_phy(pkt)
    ctx.ctrs.pkts_out += 1

def demod_thr(ctx):
    sense = filter.frequency_follow(filter.clock_recover(ctx.demoditer(), ctx.period))
    streama, streamb = itertools.tee(sense)
    syncdet = framing.sync_detect(modulate.reals(streama), ctx.sync_seq, len(ctx.sync_seq) / 2)
    bits = modulate.bpsk_demod(streamb)
    for start, buffer, errors in framing.frame_demod(bits, ctx.coder, syncdet):
        bts = modulate.bitwise_demod(modulate.differential_demod(modulate.bitstuff_demod(buffer)))
        ctx.usrq.put(bytes(bts))

class Counters:
    pkts_out = 0
    pkts_in = 0
    write_errs = 0

class Context:
    EMPTY = {}
    sample_size = 4
    period = 4
    stream = None
    sync_seq = framing.BARKER.ELEVEN
    coder = channel.Hamming()
    shaper = filter.FIRFilter.raised_cos(101, period)
    loop = False
    amplitude = 0.5

    def __init__(self, tun, phyoq, usrq):
        self.tun = tun
        self.phyoq, self.usrq = phyoq, usrq
        self.demodin, self.demoditer = iterutil.coiter()
        self.demod_thr = threading.Thread(target=demod_thr, args=(self,))
        self.demod_thr.daemon = True
        self.demod_thr.start()
        self.ctrs = Counters()

    def modulate(self, bts):
        diff = modulate.bitstuff_mod(modulate.differential_mod(modulate.bitwise_mod(bts)))
        frame = framing.frame_mod(diff, self.coder, self.sync_seq)
        signal = filter.impulse_interp(modulate.bpsk_mod(frame), self.period)
        samples = np.array(list(self.shaper.run(signal))) * self.amplitude
        return samples.astype(np.float32)

    def enqueue_phy(self, bts):
        self.phyoq.put(self.modulate(bts))

    def next_phy_out_buffer(self, frames):
        if frames not in self.EMPTY:
            self.EMPTY[frames] = bytes(frames * self.sample_size)
        out = self.EMPTY[frames]
        if self.stream is None:
            try:
                item = self.phyoq.get(False)
            except queue.Empty:
                pass
            else:
                self.stream = item
        if self.stream is not None:
            if len(self.stream) == 0:
                self.stream = None
                return out
            out = self.stream[:frames]
            if len(out) < frames:
                out = np.concatenate([out, np.zeros((frames - len(out),), np.float32)])
                self.stream = None
            else:
                self.stream = self.stream[frames:]
            out = out.tobytes()
        return out

    #sampbuf = open('/tmp/log', 'wb')
    def next_phy_in_buffer(self, buffer):
        samples = np.frombuffer(buffer, np.float32)
        #fac = np.max(np.abs(samples))
        #if fac < 1e-12:
        #    fac = 1.0
        #res = samples / fac
        res = samples
        #self.sampbuf.write(res.tobytes())
        #self.sampbuf.flush()
        self.demodin(res)

#ilog, olog = open('/tmp/ilog', 'wb'), open('/tmp/olog', 'wb')
def audio_thread(context, data_in, frames, time_info, status):
    data_out = context.next_phy_out_buffer(frames)
    #ilog.write(data_in)
    #olog.write(data_out)
    #ilog.flush()
    #olog.flush()
    context.next_phy_in_buffer(data_out if context.loop else data_in)
    return data_out, pyaudio.paContinue

def usr_thread(ctx):
    while True:
        pkt = ctx.usrq.get()
        print('o', len(pkt), pkt)
        try:
            ctx.tun.write(pkt)
        except OSError:
            ctx.ctrs.write_errs += 1
        else:
            ctx.ctrs.pkts_in += 1

parser = argparse.ArgumentParser()
parser.add_argument('--loop', action='store_true', help='Software loopback test')

RATE = 48000
async def main():
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    pa = pyaudio.PyAudio()
    phy_queue, usr_queue = Queue(), Queue()
    tun = pytun.TunTapDevice(name='doa', flags=pytun.IFF_TAP)
    ctx = Context(tun, phy_queue, usr_queue)

    ctx.loop = args.loop

    loop.add_reader(tun, recv_into, ctx)
    uthread = threading.Thread(target=usr_thread, args=(ctx,))
    uthread.daemon = True
    uthread.start()

    stream = pa.open(
            rate=RATE,
            channels=1,
            format=pyaudio.paFloat32,
            input=True,
            output=True,
            stream_callback=functools.partial(audio_thread, ctx),
            start=True,
    )

    while True:
        print(f'\r\x1b[2Kin = {ctx.ctrs.pkts_in}, out = {ctx.ctrs.pkts_out}, werr = {ctx.ctrs.write_errs}', end='', flush=True)
        await asyncio.sleep(1.0)

if __name__ == '__main__':
    asyncio.run(main())
