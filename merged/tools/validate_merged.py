import sys, os, json, collections, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rawalign as RA
from lxml import etree
XML, RAW = sys.argv[1], sys.argv[2]
RA.load(RAW)
T = "{http://www.tei-c.org/ns/1.0}"; XID = "{http://www.w3.org/XML/1998/namespace}id"
root = etree.parse(XML).getroot()   # well-formed가 아니면 여기서 실패
body = root.find(".//" + T + "body")
defined = {e.get(XID) for e in root.iter() if isinstance(e.tag, str) and e.get(XID)}
dup = [k for k, v in collections.Counter(e.get(XID) for e in root.iter() if isinstance(e.tag, str) and e.get(XID)).items() if v > 1]
undef = collections.Counter()
for e in body.iter():
    if not isinstance(e.tag, str): continue
    for a in ("ref", "who", "toWhom", "corresp", "ana", "resp"):
        for i in (e.get(a) or "").split():
            if i.startswith("#") and i[1:] not in defined:
                undef[a + ":" + i[1:]] += 1
units = list(body.iter(T + "p", T + "l"))
ev = RA.align([RA.norm(RA.txt(u)) for u in units])
c = collections.Counter(e["종류"] for e in ev)
cov = collections.Counter(g for e in ev if e["종류"] != "원문 문단 누락" for g in e.get("원문", []))
missing = [g for g in range(len(RA.raw)) if g not in cov]
twice = [g for g, k in cov.items() if k > 1]
divs = [(d.get("type"), d.get("n")) for d in body.findall(T + "div")]
res = {"well-formed": True, "중복 xml:id": dup[:10], "정의 없는 참조(종류:ID)": dict(undef.most_common(40)), "정의 없는 참조 수": sum(undef.values()),
       "대조 요약": dict(c), "원문 문단": len(RA.raw), "빠진 원문 문단": missing, "두 번 나온 원문 문단": twice,
       "div": len(divs), "chapter div": sum(1 for t, n in divs if t == "chapter"), "part div": [n for t, n in divs if t == "part"],
       "p": sum(1 for u in units if u.tag == T + "p"), "l": sum(1 for u in units if u.tag == T + "l"),
       "said": len(list(body.iter(T + "said"))), "said who 없음": sum(1 for s in body.iter(T + "said") if not s.get("who")),
       "listPerson": len(root.findall(".//" + T + "listPerson/" + T + "person")) + len(root.findall(".//" + T + "listPerson/" + T + "personGrp")),
       "그 밖의 대조 사건": [e for e in ev if e["종류"] not in ("일치",)][:40]}
print(json.dumps(res, ensure_ascii=False, indent=1)[:6000])
json.dump(res, open(XML.replace(".xml", "_검증.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
