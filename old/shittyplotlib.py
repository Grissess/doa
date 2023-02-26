import os, tempfile

def plot(xf, f, fn = None):
    if fn is None:
        fd, name = tempfile.mkstemp(suffix = '.dat', text = True)
        fo = os.fdopen(fd, 'w')
    else:
        name, fo = fn, open(fn, 'w')
    for x in range(len(xf)):
        fo.write(f'{xf[x]}\t{f(x)}\n')
    fo.flush()
    fo.close()
    return name
