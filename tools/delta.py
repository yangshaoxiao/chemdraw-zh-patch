"""MIT: generate/apply bounded COPY/LITERAL deltas without external libraries."""
import io
import struct

MAGIC = b'CDZHD1\0'


def make_delta(source: bytes, target: bytes) -> bytes:
    block = 128
    index = {}
    for offset in range(0, len(source) - block + 1, block):
        index.setdefault(source[offset:offset + block], offset)
    out = io.BytesIO()
    out.write(MAGIC + struct.pack('<Q', len(target)))
    pos = literal_start = 0
    while pos < len(target):
        offset = index.get(target[pos:pos + block]) if pos + block <= len(target) else None
        if offset is None:
            pos += 1
            continue
        if pos > literal_start:
            literal = target[literal_start:pos]
            out.write(b'\2' + struct.pack('<I', len(literal)) + literal)
        length = block
        limit = min(len(source) - offset, len(target) - pos)
        for chunk in (65536, 1024, 16, 1):
            while length + chunk <= limit and source[offset + length:offset + length + chunk] == target[pos + length:pos + length + chunk]:
                length += chunk
        out.write(b'\1' + struct.pack('<QQ', offset, length))
        pos += length
        literal_start = pos
    if pos > literal_start:
        literal = target[literal_start:pos]
        out.write(b'\2' + struct.pack('<I', len(literal)) + literal)
    out.write(b'\0')
    result = out.getvalue()
    if apply_delta(source, result) != target:
        raise ValueError('Delta round trip failed')
    return result


def apply_delta(source: bytes, delta: bytes) -> bytes:
    stream = io.BytesIO(delta)

    def read(size):
        value = stream.read(size)
        if len(value) != size:
            raise ValueError('Truncated delta')
        return value

    if read(len(MAGIC)) != MAGIC:
        raise ValueError('Unknown delta format')
    expected = struct.unpack('<Q', read(8))[0]
    if expected > 256 * 1024 * 1024:
        raise ValueError('Output too large')
    out = bytearray()
    while True:
        op = read(1)
        if op == b'\0':
            break
        if op == b'\1':
            offset, size = struct.unpack('<QQ', read(16))
            if offset > len(source) or size > len(source) - offset:
                raise ValueError('COPY out of bounds')
            data = source[offset:offset + size]
        elif op == b'\2':
            size = struct.unpack('<I', read(4))[0]
            if size > expected - len(out):
                raise ValueError('LITERAL out of bounds')
            data = read(size)
        else:
            raise ValueError('Invalid opcode')
        if len(data) > expected - len(out):
            raise ValueError('Output out of bounds')
        out.extend(data)
    if len(out) != expected or stream.read(1):
        raise ValueError('Invalid output length or trailing data')
    return bytes(out)
