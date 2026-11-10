"""Mujeong 저장소의 13개 구간 TEI를 『무정』 1–126장 통합본(v0) 하나로 합친다.

하는 일
1. 구간마다 본문 장(div)을 꺼낸다. 장 div가 없는 구간은 'part' div 하나로 감싼다.
   - 31–40은 div type="segment" → "chapter".
   - 61–70은 본문에 섞여 들어온 장 번호 표시("62\t", "🙝 🙟")로 장을 복원하고, 그 표시와 따옴표 찌꺼기를 지운다.
   - 111–120 앞머리 6문단(원문 문단 1622–1627)은 101–110의 110장과 겹치므로 101–110 쪽을 남긴다.
2. ID를 id_map 초안에 따라 바꾼다. 공통 ID가 정해지지 않은 것은 'S구간시작_원래ID'로 임시로 둔다.
3. 통합 등록부(listPerson · listPlace · listOrg · listObject)와 헤더를 새로 만든다.
원문(위키문헌) 글자는 61–70의 찌꺼기 제거 외에는 건드리지 않는다.
"""
import sys, os, re, csv, json, copy, collections, datetime
from lxml import etree

REPO, INSPECT, IDMAP, MASTER_P, MASTER_L, OUT = sys.argv[1:7]
TEI_NS = "http://www.tei-c.org/ns/1.0"
T = "{%s}" % TEI_NS
XID = "{http://www.w3.org/XML/1998/namespace}id"
XLANG = "{http://www.w3.org/XML/1998/namespace}lang"
REF_ATTRS = ("ref", "who", "corresp", "toWhom", "ana", "target", "active", "passive", "mutual", "sameAs")
TODAY = "2026-11-09"

J = json.load(open(INSPECT, encoding="utf-8"))
idmap = collections.defaultdict(dict)
for r in csv.DictReader(open(IDMAP, encoding="utf-8-sig")):
    idmap[r["구간"]][r["구간 ID"]] = r
masters = {}
for path in (MASTER_P, MASTER_L):
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        masters[r["공통 ID"]] = r

report = {"구간": [], "61-70 장 복원": [], "111-120 겹침 제거": [], "등록부 없는 참조": collections.Counter(), "임시 ID": 0}

def ids(a):
    return [x[1:] if x.startswith("#") else x for x in (a or "").split()]

def norm(s):
    s = re.sub(r"\s+", "", s)
    return s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

def section_start(sec):
    return sec.split("-")[0]

# ---------- 61–70: 장 표시로 장 복원 ----------
MARK = re.compile(r'(?:🙝\s*🙟\s*)?"?\s*(6[2-9]|70)\t"?')

def split_p_at(p, pos_text_index):
    """p 안의 텍스트 위치(문자 인덱스)에서 p를 둘로 나눈다. 그 위치가 p의 직계 텍스트(text/tail)에 있을 때만."""
    # 직계 텍스트 조각 목록: (노드, 'text'|'tail', 시작 인덱스)
    acc = 0
    segs = []
    segs.append((p, "text", acc)); acc += len(p.text or "")
    for ch in p:
        inner = "".join(ch.itertext()) if isinstance(ch.tag, str) else ""
        acc_in = acc; acc += len(inner)
        segs.append((ch, "tail", acc)); acc += len(ch.tail or "")
    for node, kind, start in segs:
        s = (node.text if kind == "text" else node.tail) or ""
        if start <= pos_text_index <= start + len(s):
            cut = pos_text_index - start
            left_s, right_s = s[:cut], s[cut:]
            newp = etree.Element(T + "p")
            if kind == "text":
                p.text = left_s
                newp.text = right_s
                for ch in list(p):
                    newp.append(ch)
            else:
                node.tail = left_s
                newp.text = right_s
                idx = list(p).index(node)
                for ch in list(p)[idx + 1:]:
                    newp.append(ch)
            return newp
    return None

def clean_text_nodes(el, pattern, repl=""):
    for e in el.iter():
        if not isinstance(e.tag, str):
            continue
        if e.text:
            e.text = pattern.sub(repl, e.text)
        if e is not el and e.tail:
            e.tail = pattern.sub(repl, e.tail)

def restore_6170(body):
    ps = list(body.iter(T + "p"))
    out = collections.OrderedDict([("61", [])])
    cur = "61"
    for p in ps:
        pieces = [p]
        # p 안에 장 표시가 여러 번일 수 있으니 반복
        while True:
            last = pieces[-1]
            full = "".join(last.itertext())
            m = MARK.search(full)
            if not m:
                break
            n = m.group(1)
            if m.start() <= 2:  # 문단 맨 앞: 표시만 지우고 그 문단부터 새 장
                newp = last
                pieces[-1] = None
                pieces.append((n, newp))
                # 표시 문자열 제거
                rm_once(newp, m.group(0))
                break
            newp = split_p_at(last, m.start())
            if newp is None:
                report["61-70 장 복원"].append({"실패": full[:40]}); break
            rm_once(newp, m.group(0).lstrip())
            pieces.append((n, newp))
            break
        for pc in pieces:
            if pc is None:
                continue
            if isinstance(pc, tuple):
                cur = pc[0]; out.setdefault(cur, []); pc = pc[1]
                report["61-70 장 복원"].append({"장": cur, "시작": "".join(pc.itertext())[:30]})
            out[cur].append(pc)
    # 따옴표 찌꺼기: 원문에는 곧은 큰따옴표(")가 없다
    for n, plist in out.items():
        for p in plist:
            clean_text_nodes(p, re.compile(r'"'))
            clean_text_nodes(p, re.compile(r'🙝\s*🙟\s*'))
            if p.text:
                p.text = p.text.lstrip()
    return out

def rm_once(p, s):
    s = s.strip()
    for e in p.iter():
        if not isinstance(e.tag, str):
            continue
        for attr in ("text", "tail") if e is not p else ("text",):
            v = getattr(e, attr)
            if v and s in v:
                setattr(e, attr, v.replace(s, "", 1)); return True
    # 조각나 있으면 정규식으로
    return False

# ---------- 본문 모으기 ----------
chapters = []   # (n 또는 'A-B', 'chapter'|'part', [elements], 구간)
registry = {}   # 최종 ID → dict
extra_defs = {"category": [], "object": [], "item": []}

def final_id(sec, old):
    r = idmap[sec].get(old)
    # 회의 결정 칸이 채워져 있으면 그것을, 없으면 공통 ID(제안)을 쓴다.
    if r and (r.get("회의 결정") or "").strip():
        return r["회의 결정"].strip()
    if r and r["공통 ID(제안)"]:
        return r["공통 ID(제안)"]
    return f"S{section_start(sec)}_{re.sub(r'[^\w.-]', '_', old)}"

for s in J["sections"]:
    sec = s["구간"]
    path = os.path.join(REPO, "TEI", sec, s["xml 파일"])
    root = etree.parse(path).getroot()
    body = root.find(".//" + T + "body")
    defined = {e.get(XID): e for e in root.iter() if isinstance(e.tag, str) and e.get(XID)}
    # 대조 결과: p 순번 → 원문 번호
    pmap = {e["p"]: e.get("원문", [None]) for e in s["대조"] if e.get("p") is not None}
    # ID 바꾸기 (본문)
    for e in body.iter():
        if not isinstance(e.tag, str):
            continue
        for a in REF_ATTRS:
            if e.get(a):
                new = []
                for i in ids(e.get(a)):
                    if i not in defined:
                        report["등록부 없는 참조"][f"{sec}:{i}"] += 1
                    new.append("#" + final_id(sec, i))
                e.set(a, " ".join(new))
        if e.get(XID):
            e.set(XID, f"S{section_start(sec)}_{e.get(XID)}")
    # 등록부 항목 모으기
    for old, el in defined.items():
        tag = etree.QName(el).localname
        if tag in ("person", "personGrp", "place", "org"):
            fid = final_id(sec, old)
            names = [re.sub(r"\s+", " ", "".join(n.itertext())).strip() for n in el if isinstance(n.tag, str) and etree.QName(n).localname in ("persName", "placeName", "orgName", "name")]
            d = registry.setdefault(fid, {"kind": collections.Counter(), "names": [], "sex": collections.Counter(), "src": [], "notes": []})
            d["kind"][tag] += 1
            for n in names:
                if n and n not in d["names"]:
                    d["names"].append(n)
            if el.get("sex"):
                d["sex"][el.get("sex")] += 1
            d["src"].append(f"{sec}:{old}")
            nt = el.find(T + "note")
            if nt is not None and "".join(nt.itertext()).strip():
                d["notes"].append(f"[{sec}] " + re.sub(r"\s+", " ", "".join(nt.itertext())).strip()[:120])
            if fid.startswith("S"):
                report["임시 ID"] += 1
        elif tag in ("category", "object", "item"):
            c = copy.deepcopy(el); c.set(XID, final_id(sec, old)); extra_defs[tag].append((sec, c))
    # 장 div
    divs = [d for d in body.iter(T + "div") if d.get("n") and d.get("type") in ("chapter", "segment")]
    if sec == "61-70" and not divs:
        out = restore_6170(body)
        for n, plist in out.items():
            chapters.append((n, "chapter", plist, sec))
    elif divs:
        for d in divs:
            kids = [c for c in d if isinstance(c.tag, str) and etree.QName(c).localname != "head"]
            chapters.append((d.get("n"), "chapter", kids, sec))
    else:
        units = list(body.iter(T + "p", T + "l"))
        kids = []
        if sec == "111-120":
            drop = [k for k, u in enumerate(units) if pmap.get(k, [None])[0] is not None and 1622 <= pmap[k][0] <= 1627]
            report["111-120 겹침 제거"] = {"p 순번": drop, "원문 문단": [pmap[k][0] for k in drop]}
            dropset = {id(units[k]) for k in drop}
        else:
            dropset = set()
        # 본문의 최상위 블록들(div/p/lg …)을 순서대로
        container = body
        tops = [c for c in container if isinstance(c.tag, str)]
        # div 하나로 감싸져 있으면 그 안으로
        while len(tops) == 1 and etree.QName(tops[0]).localname == "div":
            tops = [c for c in tops[0] if isinstance(c.tag, str)]
        for c in tops:
            if id(c) in dropset or etree.QName(c).localname == "head":
                continue
            kids.append(c)
        chapters.append((sec, "part", kids, sec))
    report["구간"].append({"구간": sec, "장": [c[0] for c in chapters if c[3] == sec]})

# ---------- 새 문서 ----------
E = lambda tag, text=None, **kw: _E(tag, text, **kw)
def _E(tag, text=None, **kw):
    el = etree.Element(T + tag)
    for k, v in kw.items():
        k = {"xml_id": XID, "xml_lang": XLANG}.get(k, k)
        el.set(k, v)
    if text is not None:
        el.text = text
    return el

tei = etree.Element(T + "TEI", nsmap={None: TEI_NS}); tei.set(XLANG, "ko")
hdr = etree.SubElement(tei, T + "teiHeader")
fd = etree.SubElement(hdr, T + "fileDesc")
ts = etree.SubElement(fd, T + "titleStmt")
ts.append(E("title", "무정", type="main", xml_lang="ko"))
ts.append(E("title", "1–126장 통합본 (v0, 공통 ID 초안 적용 · 등록부 통합 회의 전 검토용)", type="sub"))
au = E("author", "이광수")
au.append(E("idno", "0000 0001 1059 4496", type="ISNI")); au.append(E("idno", "Q495454", type="Wikidata"))
ts.append(au)
# 구간별 태깅·검수 담당(2026-11-04 과제 배정 메일 기준)
ENCODERS = {"1-10": "김경민", "11-20": "왕성운", "21-30": "김경민", "31-40": "우인진", "41-50": "고원", "51-60": "서재현",
            "61-70": "원선미", "71-80": "목소연", "81-90": "홍현영", "91-100": "김강은", "101-110": "목소연",
            "111-120": "왕성운", "121-126": "고원"}
SECS = [s["구간"] for s in J["sections"]]
for sec in SECS:
    rs = etree.SubElement(ts, T + "respStmt", attrib={XID: "enc" + sec})
    rs.append(E("resp", f"TEI 태깅·검수 ({sec.replace('-', '–')}장)"))
    rs.append(E("name", ENCODERS.get(sec, f"{sec.replace('-', '–')}장 담당 수강생")))
rs = etree.SubElement(ts, T + "respStmt", attrib={XID: "teiagent"})
rs.append(E("resp", "1차 자동 태깅(LLM 보조)")); rs.append(E("name", "TEI Agent (DeepSeek API)"))
rs = etree.SubElement(ts, T + "respStmt", attrib={XID: "merge"})
rs.append(E("resp", "구간 병합 · 공통 ID 초안"));  rs.append(E("name", "김병준 (교강사)"))
ps_ = etree.SubElement(fd, T + "publicationStmt")
ps_.append(E("publisher", "성균관대학교 국어국문학과 대학원 「한국문학텍스트와네트워크분석연구」(2026-2)"))
av = etree.SubElement(ps_, T + "availability"); lic = etree.SubElement(av, T + "licence", target="https://creativecommons.org/licenses/by/4.0/"); lic.text = "CC BY 4.0"
ps_.append(E("ptr", target="https://github.com/ByungjunKim/Mujeong"))
ps_.append(E("date", TODAY, when=TODAY))
sd = etree.SubElement(fd, T + "sourceDesc")
# 저본: 위키문헌(한국어) 『무정』. KNoTE 헤더의 bibl[@type='digitalSource'] · bibl[@type='reference'] 구성을 따른다.
from urllib.parse import quote
WS = "https://ko.wikisource.org/wiki/"
WS_MAIN = WS + quote("무정")
SUBPAGES = [(1, 20), (21, 40), (41, 60), (61, 80), (81, 100), (101, 120), (121, 126)]
def subpage_of(n):
    n = int(str(n).split("-")[0])
    for a, b in SUBPAGES:
        if a <= n <= b:
            return f"{a}장~{b}장", WS + quote(f"무정/{a}장~{b}장", safe="/~")
bibl = etree.SubElement(sd, T + "bibl", type="digitalSource"); bibl.set(XLANG, "ko")
bibl.append(E("title", "무정", level="m")); bibl.append(E("author", "이광수")); bibl.append(E("publisher", "Wikisource(한국어)"))
bibl.append(E("idno", WS_MAIN, type="wikisource"))
for a, b in SUBPAGES:
    name, url = subpage_of(a)
    bibl.append(E("ref", f"무정/{name}", type="wikisource-subpage", n=f"{a}-{b}", target=url))
bibl.append(E("note", "수강생이 위키문헌 하위 문서에서 담당 장을 복사해 원문 txt를 취득함(이 저장소 TEI/ 아래 각 구간 폴더). 위키문헌은 장마다 따로 주소가 없고 20장 단위 하위 문서로 나뉘어 있어, 본문의 각 장 div에는 그 장이 실린 하위 문서 주소를 @source로 적음.", type="acquisition"))
bibl.append(E("note", "문단 대조에는 KNoTE 저장소(https://github.com/AKS-DHLAB/KNoTE)의 rawdata에 수집된 위키문헌 『무정』 7개 파일(1,977문단)을 씀. 수집 시점의 위키문헌 판 번호는 그 파일에 기록되어 있지 않음.", type="collation"))
ref_ = etree.SubElement(sd, T + "bibl", type="reference"); ref_.set(XLANG, "ko")
ref_.append(E("title", "무정", level="m")); ref_.append(E("author", "이광수"))
ref_.append(E("title", "매일신보", level="j")); ref_.append(E("date", "1917", when="1917"))
ref_.append(E("idno", "Q12595612", type="Wikidata")); ref_.append(E("idno", "E0019237", type="encykorea"))
ref_.append(E("ref", "한국민족문화대백과사전 「무정」", target="https://encykorea.aks.ac.kr/Article/E0019237"))
ref_.append(E("note", "1917년 『매일신보』에 126회 연재(한국민족문화대백과사전). 연재 기간은 1917년 1월 1일–6월 14일로 알려져 있음. 작가·작품 식별자(ISNI, Wikidata, 민백 ID)는 KNoTE 저장소 code/작품목록.csv에서 가져옴."))
ed = etree.SubElement(hdr, T + "encodingDesc")
pd = etree.SubElement(ed, T + "projectDesc"); pd.append(E("p", "수강생 13개 구간 TEI(GitHub ByungjunKim/Mujeong, 2026-11-08 기준)를 하나로 합친 검토용 통합본. ID는 '공통 ID(제안)'를 따르고, 정해지지 않은 것은 'S구간시작_원래ID'로 임시 표기."))
edl = etree.SubElement(ed, T + "editorialDecl")
edl.append(E("p", "61–70장: 본문에 섞여 들어온 장 번호 표시와 곧은 큰따옴표를 지우고 장 div를 복원. 111–120장 앞 6문단(110장과 중복)은 101–110장 쪽을 남김. 11–20·51–60·111–120장은 장 div가 없어 div type='part'로 둠(복원 필요)."))
if extra_defs["category"]:
    cd = etree.SubElement(ed, T + "classDecl")
    tx = etree.SubElement(cd, T + "taxonomy", attrib={XID: "said-modes"})
    seen = set()
    for sec, c in extra_defs["category"]:
        if c.get(XID) not in seen:
            seen.add(c.get(XID)); tx.append(c)
pf = etree.SubElement(hdr, T + "profileDesc")
cr = etree.SubElement(pf, T + "creation"); cr.append(E("date", "1917", when="1917"))
lu = etree.SubElement(pf, T + "langUsage"); lu.append(E("language", "한국어", ident="ko"))
tc = etree.SubElement(pf, T + "textClass"); kw_ = etree.SubElement(tc, T + "keywords", scheme="local")
kw_.append(E("term", "근현대 한국문학")); kw_.append(E("term", "장편소설"))
pt = etree.SubElement(pf, T + "particDesc")
lp = etree.SubElement(pt, T + "listPerson")
so = etree.Element(T + "standOff")
lpl = etree.SubElement(so, T + "listPlace"); lor = etree.SubElement(so, T + "listOrg")

def order_key(fid):
    m = masters.get(fid)
    return (0 if (m and m.get("출처") == "교강사 별칭 표") else 1, -int(m["사용 횟수"]) if m else 0, fid)

for fid in sorted(registry, key=order_key):
    d = registry[fid]
    kind = d["kind"].most_common(1)[0][0]
    names = d["names"][:]
    m = masters.get(fid)
    if m and m["공통 이름"] and m["공통 이름"] not in names:
        names.insert(0, m["공통 이름"])
    elif m and m["공통 이름"] in names:
        names.remove(m["공통 이름"]); names.insert(0, m["공통 이름"])
    el = etree.Element(T + kind, attrib={XID: fid})
    if d["sex"] and kind == "person":
        el.set("sex", d["sex"].most_common(1)[0][0])
    nt = {"person": "persName", "personGrp": "persName", "place": "placeName", "org": "orgName"}[kind]
    for k, n in enumerate(names[:12]):
        ne = etree.SubElement(el, T + nt); ne.text = n
        if k == 0:
            ne.set("type", "main")
    note = etree.SubElement(el, T + "note", type="source-ids"); note.text = "구간 원 ID: " + ", ".join(d["src"])
    status = "임시(공통 ID 미정)" if fid.startswith("S") else ("공통 ID 초안")
    if m and m.get("메모"):
        n2 = etree.SubElement(el, T + "note", type="editorial"); n2.text = m["메모"]
    el.set("cert", "low" if fid.startswith("S") else "medium")
    (lp if kind in ("person", "personGrp") else (lpl if kind == "place" else lor)).append(el)
if extra_defs["object"]:
    lob = etree.SubElement(so, T + "listObject")
    seen = set()
    for sec, c in extra_defs["object"]:
        if c.get(XID) not in seen:
            seen.add(c.get(XID))
            # tei_all: <object>는 <objectIdentifier>로 시작해야 한다. 이름(objectName)을 그 안으로 옮긴다.
            names = [n for n in c.findall(T + "objectName")]
            if names and c.find(T + "objectIdentifier") is None:
                oi = etree.Element(T + "objectIdentifier")
                for n in names:
                    oi.append(n)
                c.insert(0, oi)
            lob.append(c)
if extra_defs["item"]:
    li = etree.SubElement(so, T + "list", type="roles")
    for sec, c in extra_defs["item"]:
        li.append(c)
rv = etree.SubElement(hdr, T + "revisionDesc")
ch = etree.SubElement(rv, T + "change", when=TODAY, who="#merge"); ch.text = "13개 구간 병합(v0). 공통 ID는 11주차(11/10) 인물 등록부 통합 회의 전 초안."
ch = etree.SubElement(rv, T + "change", when="2026-11-10", who="#merge"); ch.text = "최종 점검: tei_all(TEI P5 4.12.0) 검증 통과(61–70 object 구조 수정). 헤더에 작가·작품 식별자(ISNI · Wikidata · 민백), 위키문헌 하위 문서 주소, 장르 분류를 넣고, 각 장 div에 저본 주소(@source)를 적음. 구간별 태깅·검수 담당자 이름을 respStmt에 적음."
tei.append(so)
text = etree.SubElement(tei, T + "text"); bd = etree.SubElement(text, T + "body")

def sort_key(c):
    n = c[0]
    return int(n.split("-")[0])
for n, typ, kids, sec in sorted(chapters, key=sort_key):
    dv = etree.SubElement(bd, T + "div", type=typ, n=str(n))
    dv.set("resp", "#enc" + sec)
    dv.set("source", subpage_of(n)[1])
    if typ == "part":
        nt = etree.SubElement(dv, T + "note", type="todo"); nt.text = f"{sec.replace('-', '–')}장: 장(div) 구분 복원 필요"
    else:
        hd = etree.SubElement(dv, T + "head"); hd.text = f"{n}장"
    for k in kids:
        dv.append(k)

tree = etree.ElementTree(tei)
etree.indent(tree, space="  ")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "wb") as f:
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write(b'<?xml-model href="https://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
    f.write(etree.tostring(tree, encoding="utf-8"))
report["등록부 없는 참조"] = dict(report["등록부 없는 참조"])
report["등록부 항목"] = {"사람": len(lp), "장소": len(lpl), "기관": len(lor)}
json.dump(report, open(OUT.replace(".xml", "_병합보고.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in report.items() if k != "구간"}, ensure_ascii=False)[:2500])
