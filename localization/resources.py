# SPDX-License-Identifier: MIT
import struct

def resources(data):
    u16 = lambda o: struct.unpack_from('<H', data, o)[0]
    u32 = lambda o: struct.unpack_from('<I', data, o)[0]
    pe = u32(0x3c)
    opt = pe + 24
    dd = opt + (112 if u16(opt) == 0x20b else 96)
    sections = []
    for i in range(u16(pe + 6)):
        o = opt + u16(pe + 20) + i * 40
        sections.append((u32(o + 12), max(u32(o + 8), u32(o + 16)), u32(o + 20)))
    def off(rva):
        for va, size, raw in sections:
            if va <= rva < va + size:
                return raw + rva - va
        raise ValueError('Invalid RVA')
    base = off(u32(dd + 16))
    result = {}
    def walk(rel, path):
        o = base + rel
        for i in range(u16(o + 12) + u16(o + 14)):
            key, value = struct.unpack_from('<II', data, o + 16 + i * 8)
            if key & 0x80000000:
                s = base + (key & 0x7fffffff)
                key = data[s + 2:s + 2 + u16(s) * 2].decode('utf-16le')
            if value & 0x80000000:
                walk(value & 0x7fffffff, path + (key,))
            else:
                rva, size = struct.unpack_from('<II', data, base + value)
                result[path + (key,)] = data[off(rva):off(rva) + size]
    walk(0, ())
    return result

def field(b, p):
    start = p
    v = struct.unpack_from('<H', b, p)[0]
    p += 2
    if v == 0xffff:
        return start, p + 2, None
    if v == 0:
        return start, p, ''
    while struct.unpack_from('<H', b, p)[0]:
        p += 2
    return start, p + 2, b[start:p].decode('utf-16le')

def dialog_fields(b):
    extended = b[:4] == b'\x01\x00\xff\xff'
    style = struct.unpack_from('<I', b, 12 if extended else 0)[0]
    count = struct.unpack_from('<H', b, 16 if extended else 8)[0]
    p = 26 if extended else 18
    for _ in range(2):
        _, p, _ = field(b, p)
    a, p, text = field(b, p)
    yield a, p, text, 'title'
    if style & 0x40:
        p += 6 if extended else 2
        a, p, text = field(b, p)
        yield a, p, text, 'font'
    for _ in range(count):
        p = (p + 3) & ~3
        p += 24 if extended else 18
        _, p, _ = field(b, p)
        a, p, text = field(b, p)
        yield a, p, text, 'control'
        size = struct.unpack_from('<H', b, p)[0]
        p += size if size else 2
    if p > len(b):
        raise ValueError('Dialog overrun')

def rebuild_dialog(b, mapping):
    fields = list(dialog_fields(b))
    # Regenerate alignment before each control by reconstructing the template.
    extended = b[:4] == b'\x01\x00\xff\xff'
    style = struct.unpack_from('<I', b, 12 if extended else 0)[0]
    count = struct.unpack_from('<H', b, 16 if extended else 8)[0]
    p = 26 if extended else 18
    out = bytearray(b[:p])
    def copy_field(translate=False, font=False):
        nonlocal p
        a, p, text = field(b, p)
        target = 'Microsoft YaHei' if font else mapping.get(text, text) if translate else text
        out.extend((target + '\0').encode('utf-16le') if target != text else b[a:p])
    copy_field(); copy_field(); copy_field(True)
    if style & 0x40:
        n = 6 if extended else 2
        out.extend(b[p:p+n]); p += n
        copy_field(font=True)
    for _ in range(count):
        p = (p + 3) & ~3
        out.extend(b'\0' * ((-len(out)) % 4))
        n = 24 if extended else 18
        out.extend(b[p:p+n]); p += n
        copy_field(); copy_field(True)
        size = struct.unpack_from('<H', b, p)[0]
        n = size if size else 2
        out.extend(b[p:p+n]); p += n
    out.extend(b[p:])
    return bytes(out)

def _menu_text_fields(blob):
    if len(blob)<4:
        raise ValueError('Truncated menu header')
    version,offset=struct.unpack_from('<HH',blob,0)
    if version!=0:
        raise ValueError('Unsupported menu version')
    pos=4+offset
    if pos>len(blob) or pos%2:
        raise ValueError('Invalid menu header offset')
    result=[]
    def word():
        nonlocal pos
        if pos+2>len(blob):raise ValueError('Truncated menu item')
        value=struct.unpack_from('<H',blob,pos)[0];pos+=2;return value
    def walk(depth=0):
        nonlocal pos
        if depth>64:raise ValueError('Menu nesting limit')
        while True:
            flags=word()
            if not flags&0x10:word()
            start=pos
            while word():pass
            result.append((start,pos,blob[start:pos-2].decode('utf-16le')))
            if flags&0x10:walk(depth+1)
            if flags&0x80:return
    walk()
    return result

def menu_fields(blob):
    for start,end,text in _menu_text_fields(blob):
        yield start,end-2,text,'menu'

def rebuild_menu(blob,mapping):
    out=bytearray();cursor=0
    for start,end,text in _menu_text_fields(blob):
        out.extend(blob[cursor:start])
        target=mapping.get(text,text)
        if '\0' in target:raise ValueError('Embedded menu NUL')
        out.extend((target+'\0').encode('utf-16le'));cursor=end
    out.extend(blob[cursor:])
    return bytes(out)
