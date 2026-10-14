# SPDX-License-Identifier: MIT
"""Scoped layout adjustment for ChemDraw's analysis panel (RT_DIALOG 50130)."""
import struct
from resources import field, rebuild_dialog

TEXT = {
    2: '分子式: (&F)',
    3: '精确质量: (&EM)',
    4: '分子量: (M&W)',
    5: '质荷比: (&m/z)',
    6: '元素分析: (E&A)',
    10: '小数位数',
}
RECT = {
    2: (7, 5, 65, 9),
    3: (7, 18, 65, 9),
    4: (7, 31, 65, 9),
    5: (7, 44, 65, 9),
    6: (7, 68, 65, 9),
    7: (74, 3, 106, 13),
    8: (74, 18, 44, 9),
    9: (74, 31, 44, 9),
    10: (121, 23, 29, 9),
    11: (152, 22, 10, 12),
    12: (164, 22, 11, 13),
    13: (74, 44, 68, 22),
    14: (144, 43, 34, 23),
    15: (74, 68, 106, 16),
    1: (8, 83, 50, 11),
}


def controls(blob):
    extended = blob[:4] == b'\x01\x00\xff\xff'
    style = struct.unpack_from('<I', blob, 12 if extended else 0)[0]
    count = struct.unpack_from('<H', blob, 16 if extended else 8)[0]
    pos = 26 if extended else 18
    for _ in range(3): _, pos, _ = field(blob, pos)
    if style & 0x40:
        pos += 6 if extended else 2
        _, pos, _ = field(blob, pos)
    for _ in range(count):
        pos = (pos + 3) & ~3
        start = pos
        xy = start + (12 if extended else 8)
        ident = struct.unpack_from('<I' if extended else '<H', blob, start + (20 if extended else 16))[0]
        pos += 24 if extended else 18
        a, pos, _ = field(blob, pos); klass = blob[a:pos]
        _, pos, text = field(blob, pos)
        size = struct.unpack_from('<H', blob, pos)[0]
        pos += size if size else 2
        yield {'id': ident, 'xy_offset': xy, 'rect': struct.unpack_from('<hhhh', blob, xy),
               'text': text, 'class': klass, 'prefix': blob[start:xy]}


def adjust(blob):
    original = list(controls(blob))
    if [c['id'] for c in original] != [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 1]:
        raise ValueError('Unexpected analysis panel controls; refusing layout changes')
    mapping = {c['text']: TEXT[c['id']] for c in original if c['id'] in TEXT}
    fixed = bytearray(rebuild_dialog(blob, mapping))
    extended = fixed[:4] == b'\x01\x00\xff\xff'
    # Set dialog width to 188, height to 97
    struct.pack_into('<h', fixed, 22 if extended else 14, 188)
    struct.pack_into('<h', fixed, 24 if extended else 16, 97)
    for c in controls(fixed):
        struct.pack_into('<hhhh', fixed, c['xy_offset'], *RECT[c['id']])
    result = bytes(fixed)
    revised = list(controls(result))
    for before, after in zip(original, revised):
        assert before['id'] == after['id'] and before['class'] == after['class'] and before['prefix'] == after['prefix']
        assert after['rect'] == RECT[after['id']]
        assert after['text'] == TEXT.get(after['id'], before['text'])
        x, y, w, h = after['rect']
        assert x >= 0 and y >= 0 and x + w <= 188 and y + h <= 97
    return result
