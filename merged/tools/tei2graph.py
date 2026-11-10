# 11주차: TEI XML → 그래프(노드·관계 CSV + Neo4j 적재용 Cypher + 검증 보고서)
# 한국문학텍스트와네트워크분석연구 (2026-2) · 파이썬 표준 기능 + lxml만 사용
#
# 스키마 (속성 그래프)
#   노드:  Person · Place · Org · Object · Chapter · Paragraph(원문 텍스트 포함) · Utterance(said)
#   관계:  (Paragraph)-[:IN]->(Chapter)
#          (Person|Place|Org|Object)-[:MENTIONED_IN {surface, tag}]->(Paragraph)
#          (Person)-[:SAYS]->(Utterance)      aloud가 false가 아닌 발화
#          (Person)-[:THINKS]->(Utterance)    aloud="false" (속마음)
#          (Utterance)-[:IN]->(Paragraph)
#          (Utterance)-[:REFERS_TO {surface}]->(Person)   발화 안에서 가리킨 인물
#          (Utterance)-[:ADDRESSED_TO]->(Person)          @toWhom이 있을 때만
#          (Person)-[:RELATION {name, source}]->(Person)  <relation>이 있을 때만
#   '함께 등장'은 저장하지 않는다. 같은 문단을 공유하는지로 질의할 때 계산한다.
import re, csv, os, json, collections
from lxml import etree

TEI = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"


def load(path):
    """XML을 읽는다. well-formed가 아니면 오류 메시지를 돌려주고 복구 모드로 다시 읽는다."""
    try:
        return etree.parse(path).getroot(), None
    except etree.XMLSyntaxError as e:
        return etree.parse(path, etree.XMLParser(recover=True)).getroot(), str(e)


def text(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def ids(attr):
    return [x[1:] if x.startswith("#") else x for x in (attr or "").split() if x.strip()]


def registry(root):
    reg = {}
    label = {"person": "Person", "personGrp": "Person", "place": "Place", "org": "Org", "object": "Object"}
    name_tag = {"person": "persName", "personGrp": "persName", "place": "placeName", "org": "orgName", "object": "objectName"}
    for tag, lab in label.items():
        for el in root.iter(TEI + tag):
            i = el.get(XID)
            if not i:
                continue
            names = [text(n) for n in el.iter(TEI + name_tag[tag])] if tag == "object" else [text(n) for n in el.findall(TEI + name_tag[tag])]
            names = [n for n in names if n] or [i]
            reg[i] = {"id": i, "label": lab, "kind": tag, "name": names[0], "aliases": "|".join(names[1:]),
                      "sex": el.get("sex") or "", "cert": el.get("cert") or ""}
    return reg


def convert(root):
    reg = registry(root)
    body = root.find(".//" + TEI + "body")
    nodes = {"Person": [], "Place": [], "Org": [], "Object": [], "Chapter": [], "Paragraph": [], "Utterance": []}
    rels = collections.defaultdict(list)
    for r in reg.values():
        nodes[r["label"]].append({k: r[k] for k in ("id", "name", "aliases", "kind", "sex", "cert")})
    used = collections.Counter()
    dangling = collections.Counter()
    chapters = [d for d in body.findall(TEI + "div") if d.get("n")] or [body]
    order = 0
    for d in chapters:
        n = d.get("n", "?")
        cid = f"ch{n}"
        nodes["Chapter"].append({"id": cid, "n": n, "type": d.get("type", ""), "order": len(nodes["Chapter"]) + 1})
        for seq, p in enumerate(d.iter(TEI + "p", TEI + "l"), 1):
            order += 1
            pid = f"{cid}_p{seq}"
            nodes["Paragraph"].append({"id": pid, "chapter": n, "seq": seq, "order": order, "text": text(p)})
            rels[("IN", "Paragraph", "Chapter")].append({"start": pid, "end": cid})
            # 등장: persName · rs · placeName · orgName 의 @ref (said 안이든 밖이든)
            for el in p.iter(TEI + "persName", TEI + "rs", TEI + "placeName", TEI + "orgName", TEI + "name", TEI + "objectName"):
                for i in ids(el.get("ref")):
                    used[i] += 1
                    if i not in reg:
                        dangling[i] += 1
                        continue
                    rels[("MENTIONED_IN", reg[i]["label"], "Paragraph")].append({"start": i, "end": pid, "surface": text(el)[:40], "tag": etree.QName(el).localname})
            # 발화
            for k, s in enumerate(p.iter(TEI + "said"), 1):
                uid = f"{pid}_u{k}"
                aloud = s.get("aloud", "")
                nodes["Utterance"].append({"id": uid, "text": text(s), "aloud": aloud, "direct": s.get("direct", ""),
                                           "chapter": n, "paragraph": pid, "who": s.get("who", "")})
                rels[("IN", "Utterance", "Paragraph")].append({"start": uid, "end": pid})
                for w in ids(s.get("who")):
                    used[w] += 1
                    if w not in reg:
                        dangling[w] += 1
                        continue
                    rels[("THINKS" if aloud == "false" else "SAYS", "Person", "Utterance")].append({"start": w, "end": uid})
                for t in ids(s.get("toWhom")):
                    if t in reg:
                        rels[("ADDRESSED_TO", "Utterance", "Person")].append({"start": uid, "end": t})
                inside = {}
                for el in s.iter(TEI + "persName", TEI + "rs"):
                    for i in ids(el.get("ref")):
                        if i in reg and reg[i]["label"] == "Person":
                            inside.setdefault(i, text(el)[:40])
                for i, surf in inside.items():
                    if i not in ids(s.get("who")):
                        rels[("REFERS_TO", "Utterance", "Person")].append({"start": uid, "end": i, "surface": surf})
    for r in root.iter(TEI + "relation"):
        nm = r.get("name") or r.get("type") or "relation"
        act, pas, mut = ids(r.get("active")), ids(r.get("passive")), ids(r.get("mutual"))
        for a in act:
            for b in pas:
                rels[("RELATION", "Person", "Person")].append({"start": a, "end": b, "name": nm, "source": "listRelation"})
        for a in mut:
            for b in mut:
                if a < b:
                    rels[("RELATION", "Person", "Person")].append({"start": a, "end": b, "name": nm, "source": "listRelation"})
    report = {
        "노드": {k: len(v) for k, v in nodes.items()},
        "관계": {"-".join(k): len(v) for k, v in rels.items()},
        "등록부에 없는 ID(본문 참조)": dict(dangling.most_common()),
        "본문에서 안 쓰인 등록 ID": sorted(i for i in reg if used[i] == 0),
        "who 없는 said": sum(1 for u in nodes["Utterance"] if not u["who"]),
    }
    return nodes, dict(rels), report


def save(nodes, rels, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    for lab, rows in nodes.items():
        if not rows:
            continue
        p = os.path.join(outdir, f"nodes_{lab}.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        files.append(p)
    for (typ, a, b), rows in rels.items():
        if not rows:
            continue
        p = os.path.join(outdir, f"rels_{typ}_{a}_{b}.csv")
        keys = list(dict.fromkeys(k for r in rows for k in r))
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
        files.append(p)
    return files


CYPHER_HEAD = """// 『무정』 그래프 적재 (Neo4j 5 · AuraDB Free)
// BASE는 CSV가 있는 주소. GitHub에 올렸다면 raw 주소, 아니면 Aura 'Import'로 직접 올린다.
// MERGE를 쓰므로 같은 파일을 다시 넣어도 노드가 두 번 생기지 않는다.
:param BASE => 'https://raw.githubusercontent.com/ByungjunKim/Mujeong/main/graph/';
"""


def cypher(nodes, rels):
    out = [CYPHER_HEAD]
    for lab in nodes:
        out.append(f"CREATE CONSTRAINT {lab.lower()}_id IF NOT EXISTS FOR (n:{lab}) REQUIRE n.id IS UNIQUE;")
    for lab, rows in nodes.items():
        if not rows:
            continue
        props = ", ".join(f"n.{k} = row.{k}" for k in rows[0] if k != "id")
        out.append(f"LOAD CSV WITH HEADERS FROM $BASE + 'nodes_{lab}.csv' AS row\nMERGE (n:{lab} {{id: row.id}}) SET {props};")
    for (typ, a, b), rows in rels.items():
        if not rows:
            continue
        extra = [k for k in rows[0] if k not in ("start", "end")]
        setp = (" SET " + ", ".join(f"r.{k} = row.{k}" for k in extra)) if extra else ""
        out.append(f"LOAD CSV WITH HEADERS FROM $BASE + 'rels_{typ}_{a}_{b}.csv' AS row\nMATCH (s:{a} {{id: row.start}}), (e:{b} {{id: row.end}})\nCREATE (s)-[r:{typ}]->(e){setp};")
    return "\n\n".join(out) + "\n"


if __name__ == "__main__":
    import sys
    src, outdir = sys.argv[1], sys.argv[2]
    root, err = load(src)
    nodes, rels, rep = convert(root)
    rep["well-formed"] = "통과" if not err else "실패 — " + err
    save(nodes, rels, outdir)
    open(os.path.join(outdir, "load_neo4j.cypher"), "w", encoding="utf-8").write(cypher(nodes, rels))
    json.dump(rep, open(os.path.join(outdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1)[:3000])
