# -*- coding: utf-8 -*-
"""통합본 v0(저장소의 현재 파일, 수강생 수정 포함) → v1.
11주차(2026-11-10) 인물 등록부 통합 회의 결정을 반영한다.
사용법: python make_v1.py merged/무정_통합본_v0.xml merged/무정_통합본_v1.xml [보고.json]
본문 글자는 바꾸지 않는다(태그와 속성만 고친다)."""
import sys, json, collections, re
from lxml import etree

NS = "http://www.tei-c.org/ns/1.0"
T = "{%s}" % NS
XID = "{http://www.w3.org/XML/1998/namespace}id"

# ── 회의 결정 ────────────────────────────────────────────────
RENAME = {            # 옛 ID → 새 ID (등록부 항목은 새 ID 하나로 합친다)
    "KJH": "KGH",     # 안건 7: 김장로 = 김광현 → KGH
    "KJH_W": "KGH_W",  # 안건 1-2: 관계명 ID도 따라 바꾼다
    "PES": "PJS", "YC_FATHER": "PJS", "S81_YC_FATHER": "PJS",   # 안건 6: 박진사 · 박응진 · 영채의 아버지
    "S1_AKHAN": "AKHAN", "S11_AKHAN": "AKHAN",                  # 결정 필요 ID: 두 구간의 악한은 같은 사람
}
MAIN_NAME = {"KGH": "김장로", "PJS": "박진사", "AKHAN": "악한"}
EDITORIAL = {
    "KGH": "본명 김광현(金光鉉, 2장의 문패). 11주차 회의 결정으로 ID를 KJH에서 KGH로 바꿈.",
    "PJS": "영채의 부친. 11주차 회의 결정으로 박응진(PES) · 영채의 아버지(YC_FATHER)를 한 사람으로 합침.",
    "AKHAN": "11주차 회의 결정으로 1–10 · 11–20의 '악한'을 한 사람으로 합침.",
}
NARRATOR = ["S41_NAR", "S61_NA", "S81_NARR", "S101_NAR", "S121_NAR"]        # 안건 8: 등록 없음
DOG = ["S11_GAE"]                                                          # 안건 9: 태깅 삭제
OUTSIDE = ["JESUS", "IDORYEONG", "CHUNHYANG", "NAP", "ELLEN", "EWA", "PEST", "ADAM", "BAIJUYI",
           "CHUNHYANG_MOTHER", "DUFU", "GJ", "GOETHE", "KROPOTKIN", "LTB", "NAM_WON_BUSA", "ROUSSEAU",
           "SHAKESPEARE", "SMSY", "SODONGPA", "TAGORE", "TMG", "TOLSTOY", "WCR", "WELL", "YCG"]  # 안건 10: 등록 없음
REMOVE = set(NARRATOR + DOG + OUTSIDE)
DROP_ATTRS = ["toWhom", "ana"]     # 안건 11 · 13
REF_ATTRS = ["ref", "who", "corresp", "sameAs", "active", "passive", "mutual"]


def unwrap(el):
    """요소를 벗기고 글자와 자식은 그 자리에 남긴다."""
    parent = el.getparent()
    idx = parent.index(el)
    text = el.text or ""
    tail = el.tail or ""
    kids = list(el)
    if idx == 0:
        parent.text = (parent.text or "") + text
    else:
        prev = parent[idx - 1]
        prev.tail = (prev.tail or "") + text
    for k in kids:
        parent.insert(parent.index(el), k)
    if kids:
        kids[-1].tail = (kids[-1].tail or "") + tail
    elif idx == 0:
        parent.text = (parent.text or "") + tail
    else:
        prev = parent[idx - 1]
        prev.tail = (prev.tail or "") + tail
    parent.remove(el)


def names_of(el):
    return [("".join(n.itertext()).strip(), n) for n in el.findall(T + "persName")]


def main(src, dst, report_path=None):
    parser = etree.XMLParser(remove_blank_text=False)
    doc = etree.parse(src, parser)
    root = doc.getroot()
    body = root.find(".//" + T + "body")
    rep = collections.OrderedDict()
    text_before = "".join(body.itertext())

    # 0) 헤더: respStmt 바로 아래의 idno · email을 스키마가 허용하는 자리로 옮긴다(값은 그대로)
    moved = 0
    for rs in root.iter(T + "respStmt"):
        name = rs.find(T + "name")
        for ch in list(rs):
            if ch.tag == T + "idno" and name is not None:
                tail = ch.tail
                rs.remove(ch); ch.tail = "\n          "
                name.append(ch); moved += 1
            elif ch.tag == T + "email":
                note = etree.Element(T + "note")
                note.tail = ch.tail
                rs.replace(ch, note); ch.tail = None
                note.append(ch); moved += 1
    rep["헤더: respStmt 안 idno · email 자리 옮김"] = moved

    # 1) ID 바꾸기 · 합치기
    byid = {e.get(XID): e for e in root.iter() if isinstance(e.tag, str) and e.get(XID)}
    for new in sorted(set(RENAME.values())):
        olds = [o for o, n in RENAME.items() if n == new]
        target = byid.get(new)
        donors = [byid[o] for o in olds if o in byid]
        if target is not None and target.get("sameAs"):      # 수강생이 넣은 참조용 항목(KGH sameAs KJH)은 비우고 다시 채운다
            stub = target
            base = donors[0]
            base.set(XID, new)
            stub.getparent().remove(stub)
            target = base; donors = donors[1:]
        elif target is None:
            target = donors[0]; target.set(XID, new); donors = donors[1:]
        have = {n for n, _ in names_of(target)}
        src_notes = []
        for d in donors:
            for n, el in names_of(d):
                if n and n not in have:
                    pn = etree.SubElement(target, T + "persName"); pn.text = n
                    have.add(n)
            for nt in d.findall(T + "note"):
                if nt.get("type") == "source-ids":
                    src_notes.append((nt.text or "").replace("구간 원 ID: ", ""))
            d.getparent().remove(d)
        # 이름 순서: 대표 이름 먼저
        main = MAIN_NAME.get(new)
        if main:
            for pn in target.findall(T + "persName"):
                if pn.get("type") == "main":
                    del pn.attrib["type"]
            for n, el in names_of(target):
                if n == main:
                    el.set("type", "main"); break
        # 메모 정리: persName 뒤에 note가 오도록 다시 놓는다
        notes = target.findall(T + "note")
        for nt in notes:
            target.remove(nt)
        for nt in notes:
            if nt.get("type") == "source-ids" and src_notes:
                nt.text = (nt.text or "") + ", " + ", ".join(src_notes)
            if nt.get("type") == "editorial" and new in EDITORIAL:
                nt.text = EDITORIAL[new]
            target.append(nt)
        if new in EDITORIAL and not any(nt.get("type") == "editorial" for nt in notes):
            nt = etree.SubElement(target, T + "note", type="editorial"); nt.text = EDITORIAL[new]
        # 들여쓰기 맞춤
        kids = list(target)
        for k in kids[:-1]:
            k.tail = "\n            "
        target.text = "\n            "
        kids[-1].tail = "\n          "
    renamed = collections.Counter()
    for e in root.iter():
        if not isinstance(e.tag, str):
            continue
        for a in REF_ATTRS:
            v = e.get(a)
            if not v:
                continue
            toks = v.split()
            new = []
            for t in toks:
                k = t[1:] if t.startswith("#") else None
                if k in RENAME:
                    new.append("#" + RENAME[k]); renamed[k + "→" + RENAME[k]] += 1
                else:
                    new.append(t)
            if new != toks:
                e.set(a, " ".join(dict.fromkeys(new)))
    rep["ID 바꿈(참조 수)"] = dict(renamed)

    # 2) 등록하지 않는 대상: 본문 태그를 벗기고 등록부 항목을 지운다
    removed = collections.Counter(); who_dropped = collections.Counter()
    for e in list(body.iter()):
        if not isinstance(e.tag, str):
            continue
        for a in ("ref", "who", "corresp"):
            v = e.get(a)
            if not v:
                continue
            toks = v.split()
            keep = [t for t in toks if t.lstrip("#") not in REMOVE]
            if keep == toks:
                continue
            for t in toks:
                if t.lstrip("#") in REMOVE:
                    removed[t.lstrip("#")] += 1
            tag = e.tag.replace(T, "")
            if keep:
                e.set(a, " ".join(keep))
            elif a == "ref" and tag in ("persName", "rs", "name"):
                unwrap(e); break
            else:
                del e.attrib[a]; who_dropped[tag + "@" + a] += 1
    for i in REMOVE:
        el = byid.get(i)
        if el is not None and el.getparent() is not None:
            prev = el.getprevious()
            if prev is not None:
                prev.tail = el.tail
            el.getparent().remove(el)
    rep["태그 벗김(대상 ID별 횟수)"] = dict(removed)
    rep["속성만 지움"] = dict(who_dropped)

    # 3) @toWhom · @ana 지움. 속성이 하나도 안 남은 <seg>는 벗긴다
    dropped = collections.Counter(); seg_unwrapped = 0
    for e in list(body.iter()):
        if not isinstance(e.tag, str):
            continue
        for a in DROP_ATTRS:
            if e.get(a) is not None:
                del e.attrib[a]; dropped[a] += 1
        if e.tag == T + "seg" and not e.attrib:
            unwrap(e); seg_unwrapped += 1
    rep["속성 지움"] = dict(dropped); rep["빈 seg 벗김"] = seg_unwrapped

    # 4) 헤더 표시
    for t in root.iter(T + "title"):
        if t.get("type") == "sub":
            t.text = "1–126장 통합본 (v1, 11주차 인물 등록부 통합 회의 결정 반영)"
    rv = root.find(".//" + T + "revisionDesc")
    last = rv[-1]
    ch = etree.SubElement(rv, T + "change", when="2026-11-12", who="#merge")
    ch.text = ("v1: 수강생이 v0에 직접 고친 내용(헤더 식별자, 51–60 장 구분, 71–80 · 101–110 수정 등)을 이어받고, "
               "11주차 회의 결정을 반영함. 김장로 ID KJH → KGH, 박진사 · 박응진 · 영채의 아버지를 PJS로, "
               "1–10 · 11–20의 악한을 AKHAN으로 합침. 서술자 '나', 개, 작품 밖 인물은 등록하지 않고 본문 태그를 벗김. "
               "@toWhom · @ana를 지움. 본문 글자는 바꾸지 않음.")
    last.tail = "\n      "; ch.tail = "\n    "

    # 5) 검사
    text_after = "".join(body.itertext())
    rep["본문 글자 동일"] = (text_before == text_after)
    ids = collections.Counter(e.get(XID) for e in root.iter() if isinstance(e.tag, str) and e.get(XID))
    rep["중복 xml:id"] = [k for k, v in ids.items() if v > 1]
    und = collections.Counter()
    used = collections.Counter()
    for e in root.iter():
        if not isinstance(e.tag, str):
            continue
        for a in REF_ATTRS + ["resp", "toWhom", "ana"]:
            for v in (e.get(a) or "").split():
                if v.startswith("#"):
                    used[v[1:]] += 1
                    if v[1:] not in ids:
                        und[a + ":" + v[1:]] += 1
    rep["정의 없는 참조"] = dict(und)
    reg = [e for tag in ("person", "personGrp") for e in root.iter(T + tag)]
    rep["인물 등록(person + personGrp)"] = len(reg)
    rep["본문에서 안 쓰이는 인물 ID"] = sorted(e.get(XID) for e in reg if used[e.get(XID)] == 0)
    divs = body.findall(T + "div")
    rep["div"] = dict(collections.Counter(d.get("type") for d in divs))
    rep["p"] = sum(1 for _ in body.iter(T + "p")); rep["l"] = sum(1 for _ in body.iter(T + "l"))
    rep["said"] = sum(1 for _ in body.iter(T + "said"))
    rep["said who 없음"] = sum(1 for s in body.iter(T + "said") if not s.get("who"))

    doc.write(dst, encoding="UTF-8", xml_declaration=True)
    # XML 선언과 xml-model 줄은 원본 그대로 둔다
    orig = open(src, encoding="utf-8").read(); out = open(dst, encoding="utf-8").read()
    out = orig[:orig.index("<TEI ")] + out[out.index("<TEI "):]
    open(dst, "w", encoding="utf-8").write(out if out.endswith("\n") else out + "\n")
    if report_path:
        json.dump(rep, open(report_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return rep


if __name__ == "__main__":
    r = main(*sys.argv[1:4])
    print(json.dumps(r, ensure_ascii=False, indent=1))
