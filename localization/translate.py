# SPDX-License-Identifier: MIT
"""Deterministic UI translation only; no online service or chemical-data rewriting."""
import json, pathlib, re, collections
from chem3d_tooltips import TOOLTIPS
HERE = pathlib.Path(__file__).resolve().parent
OLD = HERE.parent
def norm(s):
    return re.sub(r'\s+', ' ', s.replace('&', '')).strip()
D = {}
for filename in ['base_dictionary.tsv', 'chem3d_dictionary.tsv']:
    p = HERE / filename
    if p.exists():
        for line in p.read_text('utf-8-sig').splitlines():
            if line.strip() and '\t' in line:
                a, b = line.split('\t', 1)
                D[norm(a)] = b
for filename, catalog in [('xml_index.tsv',[x[0] for x in json.loads((HERE/'xml_catalog.json').read_text('utf-8'))]), ('binary_index.tsv',json.loads((HERE/'binary_catalog.json').read_text('utf-8'))), ('extra_index.tsv',json.loads((HERE/'extra_unique.json').read_text('utf-8')))]:
    for line in (HERE/filename).read_text('utf-8-sig').splitlines():
        if not line.strip(): continue
        i,target=line.split('\t',1); source=catalog[int(i)]
        target=target.replace('\\n','\n')
        if '\x01' in source: target=target.replace('\\001','\x01')
        D[norm(source)]=target
D[norm('This program is linked to the missing export %Ts in the file %Ts. This machine may have an incompatible version of %Ts.')]='本程序链接到缺失的导出 %Ts（位于文件 %Ts）。本机的 %Ts 版本可能不兼容。'

glossary='''Large=大号|Medium=中号|Small=小号|Bold=粗线|Dashed=虚线|Equilibrium=平衡|Hollow=空心|No Go (Cross)=禁止反应（叉号）|No Go (Hash)=禁止反应（斜杠）|One-Sided (Left)=单侧（左）|One-Sided (Right)=单侧（右）|Resonance=共振|Retrosynthetic=逆合成|Solid=实心|Unbalanced Equilibrium=不等长平衡|Shaded=渐变|Shadowed=阴影|Open=开放|Circle=圆|Oval=椭圆|Round Rectangle=圆角矩形|Rectangle=矩形|Line=直线|Wavy=波浪线|Doubled=双线|Closed=闭合|Faded=淡化|Filled=填充|Plain=普通|Arrow End=终点箭头|Arrow Start=起点箭头|Half Arrow Left End=终点左半箭头|Half Arrow Right End=终点右半箭头|Half Left Arrow Start=起点左半箭头|Half Right Arrow Start=起点右半箭头|Enzyme=酶|Kinase=激酶|G-Protein=G 蛋白|Receptor=受体|Ion Channel=离子通道|IonChannel=离子通道|Immunoglobulin=免疫球蛋白|Nuclear Pore=核孔|NuclearPore=核孔|Helix Protein=螺旋蛋白|HelixProtein=螺旋蛋白|Membrane=膜|Membranes=膜|Golgi=高尔基体|ER=内质网|Endoplasmic Reticulum=内质网|Microorganism=微生物|Organelle=细胞器|Organelles=细胞器|Ribosome=核糖体|Ribosomes=核糖体|Mitochondrion=线粒体|Centriole=中心粒|Misc=其他图形|Star=星形|Ball=球形|Triangle=三角形|Hexagon=六边形|Octagon=八边形|Polygon=多边形|Virus=病毒|Bacterium=细菌|Bacteriophage=噬菌体|Paramecium=草履虫|Amoeba=变形虫|Cloud or Miscellaneous Shape=云形或其他形状|DNA=DNA|RNA=RNA|DNA/RNA=DNA/RNA|tRNA=tRNA|mRNA=mRNA|HIV=HIV|Amino Acid=氨基酸|Dotted/Dashed Bond=点线/虚线键|Pen=画笔|Chain=链|Chains=链|Chromatography=色谱|Colors=颜色|Ring Fill Colors=环填充颜色|Highlight Colors=突出显示颜色|Fragmentation=裂解|Query=查询|Chemical Symbols=化学符号|Brackets=括号|Drawing Elements=绘图元素|Orbitals=轨道|Curves=曲线|Structure=结构|Windows=窗口|Add-ins=附加组件|Accessories=辅助工具|Arrows=箭头|Arcs=圆弧|Multiple Bonds=多重键|Objects=对象|Text Styles=文本样式|Tools=工具|BioDraw=生物绘图|Benzene=苯|Chair Cyclohexane=椅式环己烷|Cyclobutane Ring=环丁烷环|Cycloheptane Ring=环庚烷环|Cyclohexane Ring=环己烷环|Cyclooctane Ring=环辛烷环|Cyclopentadiene Ring=环戊二烯环|Cyclopentane Ring=环戊烷环|Cyclopropane Ring=环丙烷环|Unspecified=未指定|Exactly=恰好|Up To=至多|Free Site=空闲位点|Free Sites=空闲位点|Not Allowed=不允许|Allowed=允许|Any=任意|Spiro Or Higher=螺环或更高|Fusion=稠合|Simple Ring=简单环|As Drawn=按绘图所示|No Ring Bonds=无环键|Must Be Absent=必须不存在|Must Be Present=必须存在|Inversion=反转|Retention=保持|Equal=相同|Narrow=严格|Broad=宽泛|Nonnatural=非天然|Deficient=贫化|Enriched=富集|Natural=天然|And=AND|Or=OR|Single=单键|Hashed=短划线|Wedged=楔形|Bold Wedged=粗楔形|Hollow Wedged=空心楔形|Dative=配位|Double=双键|Either=构型未定|Tautomeric=互变异构|Aromatic=芳香|Quadruple=四重键|Triple=三键|Ring Or Chain=环或链|Ring=环|Unmapped=未映射|Not Modified=未改变|Not Center=非反应中心|Make And Change=成键并改变|Change=改变|Center=中心|Make Or Break=成键或断键|Component=组分|Alternate Copolymer=交替共聚物|Copolymer=共聚物|Block Copolymer=嵌段共聚物|Random Copolymer=无规共聚物|Crosslink=交联|Any Polymer=任意聚合物|Generic=通用|Graft=接枝|Mer=聚合单元|Ordered Mixture=有序混合物|Unordered Mixture=无序混合物|Modification=修饰|Monomer=单体|Multiple Group=多重组|Multiple Group Override=覆盖多重组|SRU=结构重复单元|Head To Tail=头尾连接|Head To Head=头头连接|Either Or Uknown=任意或未知|No Flip=不翻转|Flip=翻转|Flush Left=左对齐|Flush Right=右对齐|User Defined=用户定义|Term=项|TL4=TL4|Reaction 1=反应单列|Reaction 2=反应双列|Multi Column TL4=多列 TL4|Multi Column Non TL4=多列非 TL4'''
G=dict(x.split('=',1) for x in glossary.split('|'))
def phrase(s):
    if s in G:return G[s]
    if s in D:return D[s]
    if re.fullmatch(r'[0-9]+',s):return s
    m=re.fullmatch(r'(.+?)(\s*\d+)',s)
    if m and m[1] in G:return G[m[1]]+' '+m[2].strip()
    if s.startswith('Enzyme ') and ' Kinase ' in s:
        return s.replace('Enzyme','酶').replace('Kinase','激酶')
    # Only join fully recognized terms, never translate partial unknown sentences.
    for key in sorted(G,key=len,reverse=True):
        if s.startswith(key+' '):
            tail=phrase(s[len(key)+1:])
            if tail is not None:return G[key]+' '+tail
    return None

prefixes={'Set Atom Substituent Query ':'设置原子取代基查询：','Set Atom Query Implicit Hydrogen ':'设置隐式氢查询：','Set Atom Query Ring ':'设置环查询：','Set Atom Query ':'设置原子查询：','Set Bond Type ':'设置键类型：','Set Bond Topology ':'设置键拓扑：','Set Bond Reaction Center ':'设置键反应中心：','Set Bracket Usage ':'设置括号用途：','Set Bracket Repeat Pattern ':'设置括号重复模式：','Set Bracket Flip Type ':'设置括号翻转类型：','Set Curve Style ':'设置曲线样式：','Page Definition ':'页面定义：','Individual Definition ':'单个定义：'}
G.update({'Unsaturation':'不饱和度','Reaction Stereo':'反应立体化学','Translation':'转换匹配','Isotopic Abundance':'同位素丰度','Abnormal Valence':'异常化合价','Enhance Stereochemistry':'增强立体化学'})
def generated(s):
    m=re.fullmatch(r'Press and drag to add (?:an? )?(.+)',s)
    if m:
        t=phrase(m[1]);return '按住并拖动以添加'+t if t else None
    m=re.fullmatch(r'(Show )?Generic Shape(?: (.*))?',s)
    if m:
        t=phrase(m[2]) if m[2] else '';return ('显示' if m[1] else '')+'通用形状'+('：'+t if t else '') if t is not None else None
    if s=='Show Microorganism':return '显示微生物'
    m=re.fullmatch(r'Show \(hide\) the (.+) toolbar',s)
    if m:
        t=phrase(m[1]);return '显示或隐藏'+t+'工具栏' if t else None
    m=re.fullmatch(r'Click or press and drag to add a (.+)\. Click a bond to fuse the ring\.',s)
    if m:
        t=phrase(m[1]);return '单击或按住拖动以添加'+t+'；单击化学键可稠合环' if t else None
    m=re.fullmatch(r'(\d+°) (.+)',s)
    if m:
        t=m[2].replace('Eliptical ','椭圆 ').replace('2 Headed','双头').replace('Single ','单头 ').replace('CCW','逆时针').replace('CW','顺时针')
        if not re.search('[A-Za-z]',t):return m[1]+' '+t
    m=re.fullmatch(r'(.+) \((.+)\)',s)
    if m:
        a=phrase(m[1]);b=phrase(m[2])
        if b and (a or re.fullmatch(r'(?:s|p|dxy|dz2|sigma|sp3|sp)(?: lobe)?',m[1])):return (a or m[1].replace('lobe','轨道瓣'))+'（'+b+'）'
    m=re.fullmatch(r'(Dashed|Solid) (\d+)',s)
    if m:return G[m[1]]+' '+m[2]
    m=re.fullmatch(r'(Free Sites|Up To|Exactly):(\d+)',s)
    if m:return G[m[1]]+'：'+m[2]
    m=re.fullmatch(r'Change the selected text to (\d+) points in size',s)
    if m:return '将所选文本字号设为 '+m[1]+' 磅'
    m=re.fullmatch(r'Set Text Size To (\d+)',s)
    if m:return '设置字号为 '+m[1]
    m=re.fullmatch(r'Set line color of the selected objects to palette color (\d+)',s)
    if m:return '将所选对象的线条颜色设为调色板颜色 '+m[1]
    m=re.fullmatch(r'Scale the view of the document to (\d+%)',s)
    if m:return '将文档视图缩放至 '+m[1]
    m=re.fullmatch(r'Copy the selected structure\(s\) to the clipboard as (.+)',s)
    if m:return '将所选结构复制到剪贴板，格式为 '+m[1].replace('a ','').replace('an ','').replace(' string',' 字符串').replace(' text',' 文本').replace(' data',' 数据').replace('Ball and Stick','球棍模型').replace('Stick','棍状模型').replace('Sybyl Line Notation','Sybyl 线性表示法')
    m=re.fullmatch(r'Paste the structure\(s\) from the clipboard, interpreting the text as (.+)',s)
    if m:return '从剪贴板粘贴结构，将文本按 '+m[1].replace('a ','').replace('an ','').replace(' string',' 字符串').replace(' data',' 数据').replace('Biopolymer','生物聚合物').replace('Peptide','肽链')+' 解析'
    for pre,out in prefixes.items():
        if s.startswith(pre):
            suffix=s[len(pre):]; hot=''
            m=re.fullmatch(r'(.*): (\[[^]]+\]) on bond',suffix)
            if m:suffix=m[1];hot='：在键上按 '+m[2]
            t=phrase(suffix)
            if t:return out+t+hot
    return phrase(s)

def tokens(s):
    return collections.Counter(re.findall(r'\^(?:\d+|-#)|&\d+|%(?:\d+\$)?[-+#0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:I64|ll|[hlLwT])?[diuoxXfFeEgGaAcCsSpn]|%\d+|\\001|\x01',s))
def translate(s):
    if not s:return s
    if s in TOOLTIPS:
        target=TOOLTIPS[s]
        assert s.count('\n')==target.count('\n') and s.startswith('\n')==target.startswith('\n')
        assert tokens(s)==tokens(target)
        return target
    core=norm(s)
    t=D.get(core)
    if t is None and '\t' in s:
        parts=s.split('\t')
        head=translate(parts[0])
        if head!=parts[0]:
            t=head+'\t'+'\t'.join(parts[1:])
    if t is None:
        tail=''
        for end in ['...', '…', ':']:
            if core.endswith(end):core=core[:-len(end)].rstrip();tail=end;break
        t=D.get(core) or generated(core)
        if t is not None:t+=tail
    if t is None or t==s:return s
    keys=re.findall(r'(?<!&)&([A-Za-z0-9])',s)
    if keys and not re.search(r'&[A-Za-z0-9]',t):t+='(&'+keys[0].upper()+')'
    assert tokens(s)==tokens(t),(s,t,tokens(s),tokens(t))
    # Default-button markers are protocol, not prose.
    assert s.count('DEFAULT')==t.count('DEFAULT'),(s,t)
    return t

if __name__=='__main__':
    for name,ss in [('xml',[x[0] for x in json.loads((HERE/'xml_catalog.json').read_text('utf-8'))]),('binary',json.loads((HERE/'binary_catalog.json').read_text('utf-8')))]:
        missing=[]
        for i,s in enumerate(ss):
            if translate(s)==s:missing.append((i,s))
        (HERE/(name+'_remaining.json')).write_text(json.dumps(missing,ensure_ascii=False,indent=2),'utf-8')
        print(name,'remaining',len(missing),'/',len(ss))
