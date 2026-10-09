# SPDX-License-Identifier: MIT
"""Patch only explicitly reviewed CLR UI user strings, keeping every existing token offset."""
import json,pathlib,hashlib,re,base64,struct,collections
from managed_strings import user_strings
from translate import tokens
HERE=pathlib.Path(__file__).resolve().parent;PACK=HERE/'package'
names=['ChemDrawManaged.dll','ChemDrawManaged.CDAX.dll','Revvity.ChemDraw.ChemDrawDotNET.dll']
strings=json.loads((HERE/'managed_unique.json').read_text('utf-8'));mapping={}
for line in (HERE/'managed_index.tsv').read_text('utf-8-sig').splitlines():
    if line.strip():
        i,t=line.split('\t',1);mapping[strings[int(i)]]=t.replace('\\n','\n')
def compressed(n):
    if n<0x80:return bytes([n])
    if n<0x4000:return bytes([0x80|(n>>8),n&255])
    return bytes([0xc0|(n>>24),(n>>16)&255,(n>>8)&255,n&255])
sha=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((PACK/'manifest.json').read_text('utf-8'));m['files']=[e for e in m['files'] if e['relative'] not in names]
log=[];references=json.loads((HERE/'managed_string_uses.json').read_text('utf-8-sig'))
def ui_reference(r):
    return bool(re.search(r'\b(?:set_Text|set_HeaderText|SetToolTip|SetCueText)\(',r['Next']))
for name in names:
    baseline=HERE/'baseline/bin'/name
    if not baseline.exists():baseline.write_bytes((pathlib.Path(m['roots']['bin'])/name).read_bytes())
    original=baseline.read_bytes();b=bytearray(original);changes=[];holes=[];deferred=[]
    records=list(user_strings(original));heap_base=records[0][3]-1
    refs=collections.defaultdict(list)
    for r in references:
        if r['File']==name:refs[r['Text']].append(r)
    def encoded(t):
        enc=t.encode('utf-16le')+b'\x01';return compressed(len(enc))+enc
    for pos,n,s,start in records:
        if s not in mapping or mapping[s]==s:continue
        uses=refs[s];safe=[r for r in uses if ui_reference(r)]
        # These three lists contain UI labels and are read by SelectedIndex, not text.
        if s in ['Standard','Custom','Imported'] and uses and all(r['Method']=='InitializeComponent' for r in uses):safe=uses
        if not safe:continue
        t=mapping[s];assert tokens(s)==tokens(t),(s,t)
        replacement=encoded(t);capacity=pos+n-start
        if len(safe)==len(uses):
            if len(replacement)>capacity:raise ValueError(('Translation exceeds original slot',name,s,t))
            b[start:pos+n]=replacement+b'\0'*(capacity-len(replacement))
            holes.append([start+len(replacement),pos+n])
            changes.append((start,pos+n));log.append(dict(file=name,source=s,target=t,start=start,end=pos+n,method='UI-only string slot'))
        else:deferred.append((s,t,safe,start))
    for s,t,safe,oldstart in deferred:
        replacement=encoded(t)
        hole=next((h for h in holes if h[1]-h[0]>=len(replacement)),None)
        if hole is None:raise ValueError(('No free user-string slot',s))
        newstart=hole[0];hole[0]+=len(replacement);b[newstart:newstart+len(replacement)]=replacement
        # Point only UI ldstr operands at a separate translated string; keep resource/data keys intact.
        for r in safe:
            il=base64.b64decode(r['IL']);ilstart=original.find(il)
            assert ilstart>=0 and original.find(il,ilstart+1)==-1,('Non-unique method body',r['Method'])
            at=ilstart+r['Offset'];assert original[at]==0x72
            token=struct.unpack_from('<I',original,at+1)[0];assert token==0x70000000+oldstart-heap_base
            struct.pack_into('<I',b,at+1,0x70000000+newstart-heap_base)
            changes.append((at+1,at+5))
            log.append(dict(file=name,source=s,target=t,start=at+1,end=at+5,method='UI ldstr operand only',target_string=newstart))
    # Only UI-string slots and reviewed ldstr operands may differ; all method opcodes remain untouched.
    masked=bytearray(b)
    for start,end in changes:masked[start:end]=original[start:end]
    assert bytes(masked)==original
    after={start:s for pos,n,s,start in user_strings(b)}
    for row in [x for x in log if x['file']==name]:assert after[row.get('target_string',row['start'])]==row['target']
    for s,t,safe,oldstart in deferred:assert after[oldstart]==s,'A data-binding key was changed'
    payload='bin/'+name
    (PACK/'payload'/payload).write_bytes(b);(PACK/'originals'/payload).write_bytes(original)
    m['files'].append(dict(group='bin',relative=name,payload=payload,before=sha(original),after=sha(b),legacy=None,kind='reviewed_clr_user_strings'))
m['statistics']['managed_ui_strings']=len(log)
(PACK/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),'utf-8')
(HERE/'managed_translation_audit.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),'utf-8')
print('Managed UI changes:',len(log),'modules:',len(names),'verified data-binding/resource keys, method opcodes, and all bytes outside reviewed string slots/operands')
