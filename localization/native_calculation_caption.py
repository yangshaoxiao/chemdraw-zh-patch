# SPDX-License-Identifier: MIT
"""Patch one reviewed native menu caption, retaining its original slot and all other bytes."""
import struct
SOURCE=b'Compute Properties ...\0'
TARGET='计算性质...'.encode('gbk')+b'\0'
def patch(data):
    pos=data.find(SOURCE)
    if pos<0 or data.find(SOURCE,pos+1)>=0:raise ValueError('Native caption must occur exactly once')
    pe=struct.unpack_from('<I',data,0x3c)[0];table=pe+24+struct.unpack_from('<H',data,pe+20)[0]
    section=None
    for i in range(struct.unpack_from('<H',data,pe+6)[0]):
        q=table+40*i;size,offset=struct.unpack_from('<II',data,q+16)
        if offset<=pos<offset+size:section=data[q:q+8].rstrip(b'\0')
    assert section==b'.rdata' and len(TARGET)<=len(SOURCE)
    new=data[:pos]+TARGET+b'\0'*(len(SOURCE)-len(TARGET))+data[pos+len(SOURCE):]
    assert len(new)==len(data)
    return new,dict(source=SOURCE[:-1].decode('ascii'),target=TARGET[:-1].decode('gbk'),start=pos,end=pos+len(SOURCE),encoding='Windows-936')

ALIASES={'GAMESS Interface':'GAMESS 接口','Gaussian Interface':'Gaussian 接口','Mopac Interface':'MOPAC 接口','AutoDock Interface':'AutoDock 接口'}
def patch_driver_aliases(data,name):
    """Keep native driver-name lookups consistent with the localized managed getter."""
    expected={'Chem3D.exe':{'GAMESS Interface','Gaussian Interface','Mopac Interface','AutoDock Interface'},'Chem3DCtl.ocx':{'GAMESS Interface','Gaussian Interface','Mopac Interface'}}[name]
    pe=struct.unpack_from('<I',data,60)[0];table=pe+24+struct.unpack_from('<H',data,pe+20)[0]
    regions=[]
    for i in range(struct.unpack_from('<H',data,pe+6)[0]):
        q=table+40*i;size,start=struct.unpack_from('<II',data,q+16)
        if data[q:q+8].rstrip(b'\0')==b'.rdata':regions.append((start,start+size))
    result=bytearray(data);audit=[]
    for source in expected:
        needle=source.encode('ascii')+b'\0';positions=[]
        for a,z in regions:
            pos=data.find(needle,a,z)
            if pos>=0:
                assert data.find(needle,pos+1,z)<0;positions.append(pos)
        assert len(positions)==1,(name,source)
        pos=positions[0];target=ALIASES[source].encode('gbk')+b'\0';assert len(target)<=len(needle)
        result[pos:pos+len(needle)]=target+b'\0'*(len(needle)-len(target));audit.append(dict(source=source,target=ALIASES[source],start=pos,end=pos+len(needle),encoding='Windows-936'))
    return bytes(result),audit
