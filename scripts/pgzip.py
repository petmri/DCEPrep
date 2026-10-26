"""Gzip a file using several threads (like pigz, which is not always installed).

Usage: pgzip.py SRC DEST [LEVEL]

The input is compressed in 8 MiB blocks, each as its own gzip member, and the members
are written to DEST in order. A multi-member file is a standard gzip file: gzip, zlib's
gzread (FSL), nibabel and Python's gzip module read it back as one stream.
"""
import os
import sys
import zlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor

BLOCK_SIZE = 8 << 20


def compress_block(block, level):
    # wbits=31 makes zlib write a complete gzip member (header, data, CRC32 and size)
    compressor = zlib.compressobj(level, zlib.DEFLATED, 31)
    return compressor.compress(block) + compressor.flush()


def blocks(f):
    block = f.read(BLOCK_SIZE)
    yield block  # even if empty, so an empty input still gives a valid gzip file
    while block := f.read(BLOCK_SIZE):
        yield block


def main():
    src, dest = sys.argv[1], sys.argv[2]
    level = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    workers = min(8, os.cpu_count() or 1)
    pending = deque()
    with open(src, "rb") as fin, open(dest, "wb") as fout, ThreadPoolExecutor(workers) as pool:
        # zlib releases the GIL, so the blocks compress in parallel. At most 2 blocks per
        # thread are held in memory; members are written in input order.
        for block in blocks(fin):
            pending.append(pool.submit(compress_block, block, level))
            if len(pending) >= 2 * workers:
                fout.write(pending.popleft().result())
        while pending:
            fout.write(pending.popleft().result())


if __name__ == "__main__":
    main()
