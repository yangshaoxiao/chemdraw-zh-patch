# SPDX-License-Identifier: MIT
"""Build only from immutable, hashed English baseline. Never alter installed files."""
import collections,ctypes,hashlib,html,json,pathlib,re,shutil,struct
import xml.etree.ElementTree as ET
from resources import resources,dialog_fields,rebuild_dialog,menu_fields,rebuild_menu
from analysis_layout import adjust as adjust_analysis_layout
from translate import translate,tokens
HERE=pathlib.Path(__file__).resolve().parent
BASE=HERE/'baseline';OUT=HERE/'package';OUT.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
base=json.loads((HERE/'baseline_manifest.json').read_text('utf-8'))
manifest=dict(version=base['version'],patch='0.2.4',roots=base['roots'],files=[])
log=[];stats=collections.Counter();custom=[]
def tr(s,entry,resource,kind):
    target=translate(s)
    if s and re.search('[A-Za-z\u4e00-\u9fff]',s):
        log.append(dict(file=entry['group']+'/'+entry['relative'],resource=resource,kind=kind,source=s,target=target,status='translated' if target!=s else 'retained'))
    if target!=s:stats[kind]+=1
    return target
pattern=re.compile(r'(<(?P<tag>Title|Tooltip|Text)\b[^>]*?(?<!/)>)(?P<body>.*?)(</(?P=tag)>)',re.S)
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.BeginUpdateResourceW.argtypes=[ctypes.c_wchar_p,ctypes.c_int];k.BeginUpdateResourceW.restype=ctypes.c_void_p
k.UpdateResourceW.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ushort,ctypes.c_void_p,ctypes.c_uint];k.UpdateResourceW.restype=ctypes.c_int
k.EndUpdateResourceW.argtypes=[ctypes.c_void_p,ctypes.c_int];k.EndUpdateResourceW.restype=ctypes.c_int
def rn(v):return ctypes.c_void_p(v) if isinstance(v,int) else ctypes.cast(ctypes.c_wchar_p(v),ctypes.c_void_p)
def sections(data):
    pe=struct.unpack_from('<I',data,0x3c)[0];count=struct.unpack_from('<H',data,pe+6)[0];start=pe+24+struct.unpack_from('<H',data,pe+20)[0];result={}
    for i in range(count):
        o=start+i*40;label=data[o:o+8].rstrip(b'\0');size,raw=struct.unpack_from('<II',data,o+16)
        if label!=b'.rsrc':result[label]=data[raw:raw+size]
    return result
addon={
 'Find structure from CAS Registry Number at ChemACX.com':'在 ChemACX.com 通过 CAS 登记号查找结构',
 'ChemACX.com Structure from CAS Registry Number':'ChemACX.com：通过 CAS 登记号查找结构',
 'CAS Registry Number':'CAS 登记号','Example, 108-95-2':'例如：108-95-2','Retrieving structure...':'正在获取结构...',
 'Close':'关闭','Cancel':'取消','Search':'搜索','Stop':'停止',
 'ChemDraw was not able to access the ChemACX service':'ChemDraw 无法访问 ChemACX 服务',
 'A structure with this CAS Registry Number could not be found':'未找到此 CAS 登记号对应的结构',
 'Please input CAS Registry Number':'请输入 CAS 登记号',
 'The input CAS Registry Number is invalid':'输入的 CAS 登记号无效'}
for e in base['files']:
    source=BASE/e['group']/e['relative'];b=source.read_bytes();assert sha(b)==e['before'],source
    new=b;payload=e['group']+'/'+e['relative'];target=OUT/'payload'/payload;target.parent.mkdir(parents=True,exist_ok=True)
    if e['group']=='gui':
        s=b.decode('utf-8-sig')
        def replace(m):
            body=m['body']
            if body.startswith('<![CDATA[') and body.endswith(']]>'):plain=body[9:-3]
            elif '<' in body:return m[0]
            else:plain=html.unescape(body)
            t=tr(plain,e,m['tag'],'xml')
            assert ']]>' not in t
            return m[0] if plain==t else m[1]+'<![CDATA['+t+']]>'+m[4]
        result=pattern.sub(replace,s)
        a,c=ET.fromstring(s),ET.fromstring(result)
        assert [(x.tag,x.attrib) for x in a.iter()]==[(x.tag,x.attrib) for x in c.iter()]
        new=result.encode('utf-8') if result!=s else b
    elif source.suffix.lower() in ['.dll','.exe','.ocx']:
        rr=resources(b);changes={}
        for key,blob in rr.items():
            if key[0]==4:
                ff=list(menu_fields(blob));mapping={t:tr(t,e,list(key),'menu') for _,_,t,_ in ff if t}
                if any(t!=v for t,v in mapping.items()):
                    nb=rebuild_menu(blob,mapping)
                    assert [mapping.get(t,t) for _,_,t,_ in ff]==[t for _,_,t,_ in menu_fields(nb)]
                    assert rebuild_menu(blob,{})==blob,'Menu framing changed'
                    changes[key]=nb
            elif key[0]==5:
                ff=list(dialog_fields(blob));mapping={t:tr(t,e,list(key),'dialog') for _,_,t,kind in ff if t and kind!='font'}
                if any(t!=v for t,v in mapping.items()):
                    nb=rebuild_dialog(blob,mapping)
                    assert [(kind,mapping.get(t,t) if kind!='font' else 'Microsoft YaHei') for _,_,t,kind in ff]==[(kind,t) for _,_,t,kind in dialog_fields(nb)]
                    if key[1]==50130:
                        nb=adjust_analysis_layout(nb)
                    changes[key]=nb
            elif key[0]==6:
                pos=0;out=bytearray()
                for i in range(16):
                    n=struct.unpack_from('<H',blob,pos)[0];pos+=2;s=blob[pos:pos+n*2].decode('utf-16le');pos+=n*2
                    t=tr(s,e,[*key,(key[1]-1)*16+i],'string');enc=t.encode('utf-16le');out+=struct.pack('<H',len(enc)//2)+enc
                assert pos==len(blob)
                if bytes(out)!=blob:changes[key]=bytes(out)
            elif isinstance(key[0],str) and key[0]=='STRI':
                custom.append(dict(file=payload,resource=list(key),size=len(blob),status='retained_pending_runtime_encoding_verification'))
        if changes:
            target.write_bytes(b);h=k.BeginUpdateResourceW(str(target),False)
            if not h:raise ctypes.WinError(ctypes.get_last_error())
            try:
                for (typ,rid,lang),blob in changes.items():
                    buf=ctypes.create_string_buffer(blob)
                    if not k.UpdateResourceW(h,rn(typ),rn(rid),lang,buf,len(blob)):raise ctypes.WinError(ctypes.get_last_error())
            except BaseException:k.EndUpdateResourceW(h,True);raise
            if not k.EndUpdateResourceW(h,False):raise ctypes.WinError(ctypes.get_last_error())
            new=target.read_bytes();after=resources(new)
            assert rr.keys()==after.keys()
            assert all(after[key]==changes.get(key,blob) for key,blob in rr.items())
            assert sections(b)==sections(new),'Executable code changed'
    elif e['relative'].endswith('chemdraw-addin-metadata.json'):
        obj=json.loads(b.decode('utf-8-sig'))
        for field in ['description','menuItemText']:
            s=obj[field];obj[field]=addon[s];stats['addin']+=1
        new=json.dumps(obj,ensure_ascii=False,indent=4).encode('utf-8')
    elif source.suffix=='.html':
        s=b.decode('utf-8-sig');result=s
        for a,z in addon.items():
            # Only text nodes and known translatable attributes; never ids or URLs.
            for old,repl in [('>'+a+'<','>'+z+'<'),('"'+a+'"','"'+z+'"')]:
                stats['addin']+=result.count(old);result=result.replace(old,repl)
        result=result.replace('                    Retrieving structure...','                    正在获取结构...')
        result=result.replace('<html>','<html lang="zh-CN">')
        assert re.findall(r'\b(?:id|for|src|href)="[^"]*"',s)==re.findall(r'\b(?:id|for|src|href)="[^"]*"',result)
        new=result.encode('utf-8')
    elif source.suffix=='.js':
        s=b.decode('utf-8-sig');result=s
        for a,z in addon.items():
            old="showErrorDialogWithMsg('"+a+"')";repl="showErrorDialogWithMsg('"+z+"')"
            stats['addin']+=result.count(old);result=result.replace(old,repl)
        # Verify executable syntax is unchanged after removing string contents.
        strip=lambda x:re.sub(r"'(?:\\.|[^'\\])*'", "''",x)
        assert strip(s)==strip(result)
        new=result.encode('utf-8')
    if new==b:continue
    target.write_bytes(new)
    # Ship English originals for offline recovery even when upgrading v0.1.
    original=OUT/'originals'/payload;original.parent.mkdir(parents=True,exist_ok=True);original.write_bytes(b)
    manifest['files'].append({**e,'payload':payload,'after':sha(new)})
manifest['statistics']=dict(stats)
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
(HERE/'translation_audit.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),'utf-8')
(OUT/'coverage.json').write_text(json.dumps(dict(statistics=dict(stats),retained=[x for x in log if x['status']=='retained'],custom_resources=custom,runtime_validation='pending'),ensure_ascii=False,indent=2),'utf-8')
print('Files:',len(manifest['files']),'Replacements:',dict(stats))
print('Build verified: baseline hashes, XML structure, placeholders, resource round trip, unchanged executable sections.')
