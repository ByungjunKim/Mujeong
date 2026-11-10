"""Mujeong 저장소 구간별 TEI 점검: 원문(KNoTE rawdata, 위키문헌) 문단 대조 + 구조 + 등록부."""
import sys, os, re, json, glob, collections, difflib
from lxml import etree

REPO, RAW, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
TEI = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"

def norm(s):
    s = re.sub(r"\s+", "", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return s

def txt(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()

# 1) 원문 문단(1,977) — 파일 순서대로
order = ["무정1장~20장", "무정21장~40장", "무정41장~60장", "무정61장~80장", "무정81장~100장", "무정101장~120장", "무정121장~126장"]
raw = []
for name in order:
    r = etree.parse(os.path.join(RAW, name + ".xml")).getroot()
    for p in r.iter("paragraph"):
        raw.append((name, txt(p)))
rawn = [norm(t) for _, t in raw]
index = collections.defaultdict(list)
for i, t in enumerate(rawn):
    index[t].append(i)

def ids(a):
    return [x.lstrip("#") for x in (a or "").split() if x.strip()]


def align(units):
    """구간 XML의 문단(p·l) 순서와 원문 문단 순서를 앞에서부터 맞춘다."""
    ev = []
    if not units:
        return ev
    # 시작 위치: 앞쪽 단위 몇 개가 연속으로 맞는 원문 위치
    start = None
    for k0 in range(min(10, len(units))):
        for g0 in index.get(units[k0], []):
            ok = sum(1 for d in range(1, 4) if k0 + d < len(units) and g0 + d < len(rawn) and units[k0 + d] == rawn[g0 + d])
            if ok >= 2 or (ok >= 1 and len(units) < 4):
                start = g0 - k0; break
        if start is not None:
            break
    g = max(0, start if start is not None else 0)
    k = 0
    while k < len(units):
        t = units[k]
        if not t:
            ev.append({"p": k, "종류": "빈 문단"}); k += 1; continue
        if g < len(rawn) and t == rawn[g]:
            ev.append({"p": k, "종류": "일치", "원문": [g]}); g += 1; k += 1; continue
        if g < len(rawn) and t.startswith(rawn[g]) and len(t) > len(rawn[g]):
            acc, h = "", g
            while h < len(rawn) and len(acc) < len(t):
                acc += rawn[h]; h += 1
            if acc == t:
                ev.append({"p": k, "종류": "원문 여러 문단을 합침", "원문": list(range(g, h))}); g = h; k += 1; continue
        if g < len(rawn) and rawn[g].startswith(t):
            acc, j = "", k
            while j < len(units) and len(acc) < len(rawn[g]):
                acc += units[j]; j += 1
            if acc == rawn[g]:
                ev.append({"p": k, "종류": "원문 한 문단을 쪼갬", "원문": [g], "쪼갠 수": j - k}); g += 1; k = j; continue
        # 앞쪽 원문에서 정확히 같은 문단을 찾으면 그 사이 원문은 빠진 것
        jump = next((j for j in range(g + 1, min(len(rawn), g + 25)) if rawn[j] == t), None)
        if jump is not None:
            for x in range(g, jump):
                ev.append({"p": None, "종류": "원문 문단 누락", "원문": [x], "원문 앞부분": raw[x][1][:40]})
            ev.append({"p": k, "종류": "일치", "원문": [jump]}); g = jump + 1; k += 1; continue
        if g < len(rawn):
            r = difflib.SequenceMatcher(None, rawn[g], t, autojunk=False)
            if r.ratio() >= 0.8:
                ops = [(tag, rawn[g][i1:i2], t[j1:j2]) for tag, i1, i2, j1, j2 in r.get_opcodes() if tag != "equal"]
                ev.append({"p": k, "종류": "글자 차이", "원문": [g], "유사도": round(r.ratio(), 3), "차이": ops[:8]}); g += 1; k += 1; continue
            if g + 1 < len(rawn):
                r2 = difflib.SequenceMatcher(None, rawn[g] + rawn[g + 1], t, autojunk=False)
                if r2.ratio() >= 0.9:
                    ops = [(tag, (rawn[g] + rawn[g + 1])[i1:i2], t[j1:j2]) for tag, i1, i2, j1, j2 in r2.get_opcodes() if tag != "equal"]
                    ev.append({"p": k, "종류": "합침 + 글자 차이", "원문": [g, g + 1], "유사도": round(r2.ratio(), 3), "차이": ops[:8]}); g += 2; k += 1; continue
        ev.append({"p": k, "종류": "원문에 없음", "앞부분": t[:50]}); k += 1
    return ev

report = []
for sec in sorted(os.listdir(os.path.join(REPO, "TEI")), key=lambda s: int(s.split("-")[0])):
    d = os.path.join(REPO, "TEI", sec)
    files = sorted(os.listdir(d))
    xmls = [f for f in files if f.lower().endswith(".xml")]
    info = {"구간": sec, "파일": files,
            "xml": len(xmls), "json": sum(f.lower().endswith(".json") for f in files),
            "txt": sum(f.lower().endswith(".txt") for f in files)}
    # UTF-8 검사
    bad = []
    for f in files:
        b = open(os.path.join(d, f), "rb").read()
        try:
            b.decode("utf-8")
        except UnicodeDecodeError:
            bad.append(f)
    info["utf8 아님"] = bad
    info["BOM"] = [f for f in files if open(os.path.join(d, f), "rb").read(3) == b"\xef\xbb\xbf"]
    if not xmls:
        report.append(info); continue
    xf = xmls[0]
    info["xml 파일"] = xf
    path = os.path.join(d, xf)
    err = None
    try:
        root = etree.parse(path).getroot()
    except etree.XMLSyntaxError as e:
        err = str(e)
        root = etree.parse(path, etree.XMLParser(recover=True)).getroot()
    info["well-formed"] = "통과" if not err else "실패: " + err[:160]
    body = root.find(".//" + TEI + "body")
    divs = [dv for dv in body.iter(TEI + "div") if dv.get("n")] if body is not None else []
    info["div"] = [(dv.get("type"), dv.get("n"), len(list(dv.iter(TEI + "p")))) for dv in divs]
    ps = [e for e in body.iter(TEI + "p", TEI + "l")] if body is not None else []
    info["p 수"] = sum(1 for e in ps if e.tag == TEI + "p")
    info["l 수"] = sum(1 for e in ps if e.tag == TEI + "l")
    info["p 안의 p"] = sum(1 for p in ps if any(a.tag == TEI + "p" for a in p.iterancestors()))
    ev = align([norm(txt(p)) for p in ps])
    info["대조"] = ev
    c = collections.Counter(e["종류"] for e in ev)
    info["대조 요약"] = dict(c)
    cov = [g for e in ev for g in e.get("원문", [])]
    if cov:
        info["원문 범위(전역 문단 번호)"] = [min(cov), max(cov)]
    # 등록부
    reg = {}
    for kind, tag in [("person", "person"), ("personGrp", "personGrp"), ("place", "place"), ("org", "org")]:
        for el in root.iter(TEI + tag):
            i = el.get(XID)
            if not i:
                continue
            names = [txt(n) for n in el if n.tag in (TEI + "persName", TEI + "placeName", TEI + "orgName", TEI + "name")]
            reg[i] = {"kind": kind, "names": [n for n in names if n], "sex": el.get("sex"),
                      "note": txt(el.find(TEI + "note")) if el.find(TEI + "note") is not None else ""}
    info["등록부"] = reg
    used = collections.Counter()
    if body is not None:
        for el in body.iter():
            for a in ("ref", "who", "corresp"):
                for i in ids(el.get(a)):
                    used[i] += 1
    info["사용 횟수"] = dict(used)
    info["등록부에 없는 ID"] = sorted(i for i in used if i not in reg)
    info["안 쓰인 등록 ID"] = sorted(i for i in reg if used[i] == 0)
    said = list(body.iter(TEI + "said")) if body is not None else []
    info["said"] = len(said)
    info["who 없는 said"] = sum(1 for s in said if not s.get("who"))
    info["태그 수"] = dict(collections.Counter(etree.QName(e).localname for e in body.iter() if isinstance(e.tag, str))) if body is not None else {}
    info["relation"] = len(list(root.iter(TEI + "relation")))
    report.append(info)

json.dump({"raw_total": len(raw), "raw": [t for _, t in raw], "sections": report}, open(OUT, "w"), ensure_ascii=False, indent=1)
for r in report:
    print(r["구간"], "xml", r["xml"], "json", r["json"], "txt", r["txt"], "| utf8X", r["utf8 아님"], "|", r.get("well-formed"),
          "| div", len(r.get("div", [])), "p", r.get("p 수"), "l", r.get("l 수"), "|", r.get("대조 요약"), "| range", r.get("원문 범위(전역 문단 번호)"),
          "| reg", len(r.get("등록부", {})), "undef", len(r.get("등록부에 없는 ID", [])), "said", r.get("said"), "nowho", r.get("who 없는 said"))
