# SPDX-License-Identifier: MIT
"""Read embedded .NET ResourceWriter v2 string values without loading code."""
import struct
MAGIC=bytes.fromhex('cecaefbe')
def read7(b,p):
    value=0
    for shift in range(0,35,7):
        v=b[p];p+=1;value|=(v&127)<<shift
        if not v&128:return value,p
    raise ValueError('Invalid 7-bit integer')
def write7(n):
    out=bytearray()
    while n>=128:out.append((n&127)|128);n>>=7
    out.append(n);return bytes(out)
def string_records(b):
    scan=0
    while True:
        base=b.find(MAGIC,scan)
        if base<0:return
        scan=base+4
        length=struct.unpack_from('<I',b,base-4)[0]
        assert base+length<=len(b)
        version,skip=struct.unpack_from('<II',b,base+4);assert version==1
        p=base+12+skip
        version,count,types=struct.unpack_from('<III',b,p);p+=12;assert version==2
        for _ in range(types):n,p=read7(b,p);p+=n
        p=base+((p-base+7)&~7)
        p+=count*4
        positions=struct.unpack_from('<'+'I'*count,b,p);p+=count*4
        data=base+struct.unpack_from('<I',b,p)[0];names=p+4
        for rel in positions:
            q=names+rel;n,q=read7(b,q);key=b[q:q+n].decode('utf-16le');q+=n
            val=data+struct.unpack_from('<I',b,q)[0]
            kind,pos=read7(b,val)
            if kind!=1:continue
            start=pos;n,pos=read7(b,pos)
            assert pos+n<=base+length
            yield key,b[pos:pos+n].decode('utf-8'),start,pos+n,q,data,base

def string_values(b):
    for row in string_records(b):yield row[:4]

def resource_sets(b):
    """Return name-offset fields and full opaque data blocks for lossless compaction."""
    scan=0
    while (base:=b.find(MAGIC,scan))>=0:
        scan=base+4;length=struct.unpack_from('<I',b,base-4)[0]
        version,skip=struct.unpack_from('<II',b,base+4);assert version==1
        p=base+12+skip;version,count,types=struct.unpack_from('<III',b,p);p+=12;assert version==2
        for _ in range(types):n,p=read7(b,p);p+=n
        p=base+((p-base+7)&~7);p+=count*4
        positions=struct.unpack_from('<'+'I'*count,b,p);p+=count*4
        data=base+struct.unpack_from('<I',b,p)[0];names=p+4;entries=[]
        for rel in positions:
            q=names+rel;n,q=read7(b,q);key=b[q:q+n].decode('utf-16le');q+=n
            at=data+struct.unpack_from('<I',b,q)[0];entries.append((key,q,at))
        yield data,base+length,entries
