# SPDX-License-Identifier: MIT
"""Translate reviewed ChemOffice Excel UI only; ribbon IDs, schema and formulas are immutable."""
import json,pathlib,re,hashlib
from build_calculations import patch
from dotnet_resources import string_values
from translate import translate,tokens
HERE=pathlib.Path(__file__).resolve().parent
NAME='CambridgeSoft.ChemOffice.ChemDrawExcel.AddIn.dll'
def norm(s):return re.sub(r'\s+',' ',s.replace('&','')).strip().casefold()
D={}
for line in (HERE/'excel_dictionary.tsv').read_text('utf-8-sig').splitlines():
    if line.strip():a,b=line.split('\t',1);D[norm(a)]=b

def excel_translate(s):
    target=D.get(norm(s))
    if target is None:return translate(s)
    keys=re.findall(r'(?<!&)&([A-Za-z0-9])',s)
    if keys and not re.search(r'&[A-Za-z0-9]',target):target+='(&'+keys[0].upper()+')'
    assert tokens(s)==tokens(target)
    assert re.findall(r'\{\d+[^}]*\}',s)==re.findall(r'\{\d+[^}]*\}',target)
    return target

def selected(key):return key.startswith(('Cmd_','Ctl_','Ttp_')) or key.endswith(('.Text','.ToolTip'))

if __name__=='__main__':
    pack=HERE/'package';m=json.loads((pack/'manifest.json').read_text('utf-8'))
    original=(HERE/'baseline/bin'/NAME).read_bytes()
    refs=json.loads((HERE/'excel_string_uses.json').read_text('utf-8-sig'))
    out,audit=patch(original,refs,resource_selector=selected,text_translator=excel_translate,skip_oversized_resources=True)
    before=list(string_values(original));after=list(string_values(out));assert len(before)==len(after)
    for old,new in zip(before,after):
        assert old[0]==new[0]
        if not selected(old[0]):assert old[1]==new[1],('Non-UI resource changed',old[0])
    assert [s for k,s,a,z in before if k=='Ribbon']==[s for k,s,a,z in after if k=='Ribbon'],'Ribbon callbacks or IDs changed'
    actual=[r for r in audit if not r.get('status')];deferred=[r for r in audit if r.get('status')]
    assert actual
    (pack/'payload/bin'/NAME).write_bytes(out);(pack/'originals/bin'/NAME).write_bytes(original)
    sha=lambda b:hashlib.sha256(b).hexdigest()
    m['patch']='0.2.5';m['files']=[e for e in m['files'] if e['relative']!=NAME]
    m['files'].append(dict(group='bin',relative=NAME,payload='bin/'+NAME,before=sha(original),after=sha(out),legacy=None,kind='reviewed_excel_ui'))
    m['statistics']['excel_ui_strings']=len(actual)
    (pack/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),'utf-8')
    (HERE/'excel_translation_audit.json').write_text(json.dumps(dict(changed=actual,deferred=deferred),ensure_ascii=False,indent=2),'utf-8')
    print('Excel UI replacements:',len(actual),'; deferred:',len(deferred),'; resource keys:',len(before),'; ribbon XML and non-UI values unchanged')
