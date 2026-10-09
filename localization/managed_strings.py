# SPDX-License-Identifier: MIT
"""Inspect the CLR user-string heap without loading or executing an assembly."""
import struct,pathlib,json
def user_strings(b):
    u16=lambda o:struct.unpack_from('<H',b,o)[0]
    u32=lambda o:struct.unpack_from('<I',b,o)[0]
    pe=u32(0x3c);opt=pe+24;dd=opt+(112 if u16(opt)==0x20b else 96);table=opt+u16(pe+20)
    def off(rva):
        for i in range(u16(pe+6)):
            o=table+i*40;va=u32(o+12);size=max(u32(o+8),u32(o+16))
            if va<=rva<va+size:return u32(o+20)+rva-va
        raise ValueError(rva)
    cli=off(u32(dd+14*8));meta=off(u32(cli+8));assert b[meta:meta+4]==b'BSJB'
    pos=meta+16+u32(meta+12);pos=(pos+3)&~3;count=u16(pos+2);pos+=4
    heap=None
    for _ in range(count):
        start,size=u32(pos),u32(pos+4);pos+=8;end=b.index(0,pos);name=b[pos:end].decode('ascii');pos=(end+4)&~3
        if name=='#US':heap=(meta+start,size)
    assert heap
    base,size=heap;pos=base+1
    while pos<base+size:
        start=pos;first=b[pos];pos+=1
        if first&0x80==0:n=first
        elif first&0xc0==0x80:n=((first&0x3f)<<8)|b[pos];pos+=1
        else:n=((first&0x1f)<<24)|(b[pos]<<16)|(b[pos+1]<<8)|b[pos+2];pos+=3
        if not n:continue
        assert n%2==1 and pos+n<=base+size
        yield pos,n,b[pos:pos+n-1].decode('utf-16le'),start
        pos+=n

if __name__=='__main__':
    here=pathlib.Path(__file__).resolve().parent;root=pathlib.Path(r'C:\Program Files\RevvitySignalsSoftware\ChemDrawApplications_x64');out=[]
    for name in ['ChemDrawManaged.dll','ChemDrawManaged.CDAX.dll','Revvity.ChemDraw.ChemDrawDotNET.dll']:
        for pos,n,s,start in user_strings((root/name).read_bytes()):out.append(dict(file=name,offset=pos,length=n,text=s,token_offset=start))
    (here/'managed_user_strings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
    ss=list(dict.fromkeys(x['text'] for x in out));(here/'managed_unique.json').write_text(json.dumps(ss,ensure_ascii=False,indent=2),'utf-8')
    for i,s in enumerate(ss):
        if s and any(c.isalpha() for c in s):print(i,repr(s))
