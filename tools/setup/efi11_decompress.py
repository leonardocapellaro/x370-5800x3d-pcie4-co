#!/usr/bin/env python3
"""EFI 1.1 / Tiano decompressor (LZ77+Huffman, the public EDK2
BaseTools/Decompress.c algorithm), pure stdlib.

Used to read ASUS `.CMO` user profiles (the file is this format; see
`cmo_parse.py` for the inner layout). Round-trips byte-exactly against the
EDK2 reference compressor (`efitool.c`) on our test inputs.

Usage: efi11_decompress.py <input> <output> [pbit]
  pbit: position-table Huffman code bits (4 or 5). If omitted, both are tried.
"""
import struct, sys

NC = 510      # number of main codes
CBIT = 9      # bits for the code-length-table count
NT = 19       # code-length code count for the code-length table itself
TBIT = 5      # bits for that table
MAXNP = 31    # max number of position codes

class Bits:
    """MSB-first bit reader over the compressed stream."""
    def __init__(s, data):
        s.v = int.from_bytes(data + b'\0' * 64, 'big')
        s.n = (len(data) + 64) * 8
        s.p = 0
    def peek(s, k):
        return (s.v >> (s.n - s.p - k)) & ((1 << k) - 1)
    def bit(s, off):
        return (s.v >> (s.n - s.p - off - 1)) & 1
    def skip(s, k):
        s.p += k
    def get(s, k):
        r = s.peek(k) if k else 0
        s.p += k
        return r

def make_table(nchar, bitlen, tbits, table, left, right):
    """Build the EDK2-style Huffman lookup table (direct + chained subtrees)."""
    count = [0] * 17
    start = [0] * 18
    weight = [0] * 17
    for i in range(nchar):
        count[bitlen[i]] += 1
    for i in range(1, 17):
        start[i + 1] = (start[i] + (count[i] << (16 - i))) & 0xffff
    if start[17] != 0:
        raise ValueError('bad code-length table')
    ju = 16 - tbits
    for i in range(1, tbits + 1):
        start[i] >>= ju
        weight[i] = 1 << (tbits - i)
    for i in range(tbits + 1, 17):
        weight[i] = 1 << (16 - i)
    i = start[tbits + 1] >> ju
    if i != 0:
        k = 1 << tbits
        while i != k:
            table[i] = 0
            i += 1
    avail = nchar
    mask = 1 << (15 - tbits)
    for ch in range(nchar):
        ln = bitlen[ch]
        if ln == 0:
            continue
        nxt = start[ln] + weight[ln]
        if ln <= tbits:
            for i in range(start[ln], nxt):
                table[i] = ch
        else:
            k = start[ln]
            arr = table
            idx = k >> ju
            i = ln - tbits
            while i:
                if arr[idx] == 0:
                    right[avail] = left[avail] = 0
                    arr[idx] = avail
                    avail += 1
                node = arr[idx]
                if k & mask:
                    arr = right
                else:
                    arr = left
                idx = node
                k = (k << 1) & 0xffff
                i -= 1
            arr[idx] = ch
        start[ln] = nxt

def decompress(src, pbit=None):
    """Return (plain, pbit, bytes_used, compressed_size)."""
    csize, osize = struct.unpack_from('<II', src, 0)
    if pbit is None:
        for pb in (4, 5):
            try:
                return decompress(src, pb)
            except Exception as e:
                err = e
        raise err
    b = Bits(src[8:8 + csize])
    left = [0] * (2 * NC)
    right = [0] * (2 * NC)
    clen = [0] * NC
    ptlen = [0] * 32
    ctable = [0] * 4096
    pttable = [0] * 256
    out = bytearray()

    def read_pt(nn, nbit, special):
        """Read one Huffman code-length table (used for code lengths and for
        position codes)."""
        n = b.get(nbit)
        if n == 0:
            c = b.get(nbit)
            for i in range(256):
                pttable[i] = c
            for i in range(nn):
                ptlen[i] = 0
            return
        i = 0
        while i < n:
            c = b.peek(3)
            if c == 7:
                o = 3
                while b.bit(o):
                    o += 1
                    c += 1   # inside the loop: one increment per set bit
            b.skip(3 if c < 7 else c - 3)
            ptlen[i] = c
            i += 1
            if i == special:
                z = b.get(2)
                for _ in range(z):
                    ptlen[i] = 0
                    i += 1
        while i < nn:
            ptlen[i] = 0
            i += 1
        make_table(nn, ptlen, 8, pttable, left, right)

    def read_c():
        """Read the main code-length table."""
        n = b.get(CBIT)
        if n == 0:
            c = b.get(CBIT)
            for i in range(NC):
                clen[i] = 0
            for i in range(4096):
                ctable[i] = c
            return
        i = 0
        while i < n:
            c = pttable[b.peek(8)]
            o = 8
            while c >= NT:
                c = right[c] if b.bit(o) else left[c]
                o += 1
            b.skip(ptlen[c])
            if c <= 2:
                if c == 0:
                    z = 1
                elif c == 1:
                    z = b.get(4) + 3
                else:
                    z = b.get(CBIT) + 20
                for _ in range(z):
                    clen[i] = 0
                    i += 1
            else:
                clen[i] = c - 2
                i += 1
        while i < NC:
            clen[i] = 0
            i += 1
        make_table(NC, clen, 12, ctable, left, right)

    blk = 0
    while len(out) < osize:
        if blk == 0:
            blk = b.get(16)          # remaining block count
            read_pt(NT, TBIT, 3)
            read_c()
            read_pt(MAXNP, pbit, -1)
        blk -= 1
        c = ctable[b.peek(12)]
        o = 12
        while c >= NC:
            c = right[c] if b.bit(o) else left[c]
            o += 1
        b.skip(clen[c])
        if c < 256:
            out.append(c)
        else:
            n = c - 253              # run length
            v = pttable[b.peek(8)]
            o = 8
            while v >= MAXNP:
                v = right[v] if b.bit(o) else left[v]
                o += 1
            b.skip(ptlen[v])
            pos = v
            if v > 1:
                pos = (1 << (v - 1)) + b.get(v - 1)
            di = len(out) - pos - 1
            if di < 0:
                raise ValueError('back-reference before start of output')
            for _ in range(n):
                out.append(out[di])
                di += 1
                if len(out) >= osize:
                    break
    used = (b.p + 7) // 8
    return bytes(out[:osize]), pbit, used, csize

if __name__ == '__main__':
    src = open(sys.argv[1], 'rb').read()
    out, pb, used, cs = decompress(src, int(sys.argv[3]) if len(sys.argv) > 3 else None)
    open(sys.argv[2], 'wb').write(out)
    print('pbit=%d out=%d bytes_used=%d of %d' % (pb, len(out), used, cs))
