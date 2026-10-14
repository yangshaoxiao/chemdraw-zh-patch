# SPDX-License-Identifier: MIT
"""Localize calculation-driver UI slots only; preserve resource keys and command tokens."""
import json,pathlib,hashlib,re,struct,base64,collections
from managed_strings import user_strings
from dotnet_resources import string_values,string_records,resource_sets,write7
from translate import translate,tokens
HERE=pathlib.Path(__file__).resolve().parent
NAMES=['AutoDockUI.dll','CambridgeSoft.ChemOffice.ConflexDriver.dll','CambridgeSoft.ChemOffice.GamessDriver.dll','CambridgeSoft.ChemOffice.GaussianDriver.dll','CambridgeSoft.ChemOffice.MopacDriver.dll','CambridgeSoft.ChemOffice.DriverShared.dll']
MENU_KEYS={'kCreateInputFile','kAdvancedMode','kRunInputFile','kPredictIR','kPredictNMR','kPredictUVVis','kMinimization','kOptimizeToTransitionState','kFrequency','kPredictIRRaman','kComputeProperties','kSpectralAnalysis'}
def ui_reference(r):
    if re.search(r'\b(?:set_Text|set_HeaderText|SetToolTip|SetCueText|AppendMenu)\(',r['Next']):return True
    if r['Type'].endswith('.Driver') and r['Method']=='get_Name' and r['Text'].endswith(' Interface'):return True
    # AutoDock uses its window caption to find an already-open dialog. Keep both copies consistent.
    return r['File']=='AutoDockUI.dll' and r['Method']=='isAutodockUIShow' and r['Text']=='AutoDock Interface' and 'Contains(' in r['Next']
def legacy_driver_caption(text):
    # COEA fixes the calling thread culture to en-US: its ANSI bridge emits CP1252.
    # Represent CP936 menu bytes reversibly in that bridge; keep managed dialog text Unicode.
    return text.encode('gbk').decode('cp1252')
def compressed(n):
    if n<128:return bytes([n])
    if n<16384:return bytes([128|(n>>8),n&255])
    return bytes([192|(n>>24),(n>>16)&255,(n>>8)&255,n&255])
def patch(original,refs):
    b=bytearray(original);changes=[];audit=[];holes=[];deferred=[]
    rows=list(user_strings(original));heap=rows[0][3]-1
    by=collections.defaultdict(list)
    for r in refs:by[r['Text']].append(r)
    for pos,n,s,start in rows:
        t=translate(s);uses=by[s];safe=[r for r in uses if ui_reference(r)]
        if t==s or not safe or len(s.strip())<=1:continue
        wire=[r for r in safe if r['Type'].endswith('.Driver') and r['Method']=='get_Name']
        normal=[r for r in safe if r not in wire]
        if wire and normal:
            w=legacy_driver_caption(t);enc=w.encode('utf-16le')+b'\x01';rep=compressed(len(enc))+enc
            deferred.append((s,w,wire,start,rep));safe=normal
        elif wire:t=legacy_driver_caption(t)
        assert tokens(t)==tokens(s)
        enc=t.encode('utf-16le')+b'\x01';rep=compressed(len(enc))+enc
        if len(safe)!=len(uses) or len(rep)>pos+n-start:deferred.append((s,t,safe,start,rep));continue
        b[start:pos+n]=rep+b'\0'*(pos+n-start-len(rep));changes.append((start,pos+n));holes.append([start+len(rep),pos+n]);audit.append(dict(source=s,target=t,kind='CLR UI',start=start,end=pos+n))
    for s,t,safe,old,rep in deferred:
        h=next((h for h in holes if h[1]-h[0]>=len(rep)),None)
        if h is None:raise ValueError(('No safe string hole',s))
        at=h[0];h[0]+=len(rep);b[at:at+len(rep)]=rep;changes.append((at,at+len(rep)))
        for r in safe:
            il=base64.b64decode(r['IL']);p=original.find(il);assert p>=0 and original.find(il,p+1)<0
            q=p+r['Offset'];assert original[q]==0x72 and struct.unpack_from('<I',original,q+1)[0]==0x70000000+old-heap
            struct.pack_into('<I',b,q+1,0x70000000+at-heap);changes.append((q+1,q+5))
        assert {start:s for pos,n,s,start in user_strings(b)}[old]==s
        audit.append(dict(source=s,target=t,kind='CLR UI operand only',start=at,end=at+len(rep)))
    values={a-1:(key,source) for key,source,a,z,*_ in string_records(original)}
    for data,end,entries in resource_sets(original):
        starts=sorted(set(at for key,q,at in entries));limits=dict(zip(starts,starts[1:]+[end]))
        packed=bytearray();offsets={};modified=False
        for at in starts:
            offsets[at]=data+len(packed)
            source_info=values.get(at)
            if source_info:
                key,source=source_info
                target=translate(source) if (key.endswith('.Text') or key.endswith('.ToolTip') or key in MENU_KEYS) and len(source.strip())>1 else source
                assert tokens(source)==tokens(target)
                encoded=target.encode('utf-8');block=b'\x01'+write7(len(encoded))+encoded
                if target!=source:
                    modified=True;audit.append(dict(source=source,target=target,kind='embedded UI resource',key=key,start=at,end=limits[at]))
                packed.extend(block)
            else:packed.extend(original[at:limits[at]])
        if not modified:continue
        if len(packed)>end-data:raise ValueError(('Resource UI data exceeds original stream',end-data,len(packed)))
        b[data:end]=packed+b'\0'*(end-data-len(packed));changes.append((data,end))
        for key,q,at in entries:
            struct.pack_into('<I',b,q,offsets[at]-data);changes.append((q,q+4))
    masked=bytearray(b)
    for a,z in changes:masked[a:z]=original[a:z]
    assert bytes(masked)==original and len(b)==len(original)
    # Parsing must still recover identical names and every unaffected value.
    before=list(string_values(original));after=list(string_values(b));assert len(before)==len(after)
    for old,new in zip(before,after):assert old[0]==new[0] and (new[1]==old[1] or new[1]==translate(old[1]))
    return bytes(b),audit
if __name__=='__main__':
    refs=json.loads((HERE/'calculation_string_uses.json').read_text('utf-8-sig'))
    pack=HERE/'package';m=json.loads((pack/'manifest.json').read_text('utf-8'));m['files']=[e for e in m['files'] if e['relative'] not in NAMES];log=[]
    for name in NAMES:
        print('Processing',name,flush=True)
        original=(HERE/'baseline/bin'/name).read_bytes();out,rows=patch(original,[r for r in refs if r['File']==name]);assert rows,name
        (pack/'payload/bin'/name).write_bytes(out);(pack/'originals/bin'/name).write_bytes(original)
        sha=lambda b:hashlib.sha256(b).hexdigest()
        m['files'].append(dict(group='bin',relative=name,payload='bin/'+name,before=sha(original),after=sha(out),legacy=None,kind='reviewed_calculation_ui'))
        log.extend(dict(file=name,**r) for r in rows)
    from native_calculation_caption import patch as patch_native
    entry=next(e for e in m['files'] if e['group']=='bin' and e['relative']=='Chem3D.exe')
    target=pack/'payload'/entry['payload'];new,row=patch_native(target.read_bytes());target.write_bytes(new);entry['after']=sha(new)
    log.append(dict(file='Chem3D.exe',kind='native menu caption',**row))
    from native_calculation_caption import patch_driver_aliases
    for name in ('Chem3D.exe','Chem3DCtl.ocx'):
        entry=next(e for e in m['files'] if e['group']=='bin' and e['relative']==name)
        target=pack/'payload'/entry['payload'];new,rows=patch_driver_aliases(target.read_bytes(),name);target.write_bytes(new);entry['after']=sha(new)
        log.extend(dict(file=name,kind='native driver-name alias',**row) for row in rows)
    m['statistics']['calculation_ui_strings']=len(log)
    (pack/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),'utf-8')
    (HERE/'calculation_translation_audit.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),'utf-8')
    print('Calculation UI changes:',len(log),'modules:',len(NAMES),'verified exact byte ranges and resource keys')
