# 11주차: TEI 통합본 → CIDOC CRM(RDF/Turtle) — 표준 온톨로지 규약 적용
# 한국문학텍스트와네트워크분석연구 (2026-2)
#
# 규약 (CIDOC CRM 7.1.x, RDFS 이름공간 http://www.cidoc-crm.org/cidoc-crm/)
#  1. 클래스·속성은 표준 이름 그대로: E21_Person, P67_refers_to … (번호_영문 이름)
#  2. 이름은 문자열 속성이 아니라 E41 Appellation 노드로 (P1 is identified by), ID는 E42 Identifier로
#  3. 분류는 E55 Type으로 (P2 has type)
#  4. 표준에 없는 것은 '확장'하되 반드시 기존 클래스·속성의 하위(subClassOf · subPropertyOf)로 선언
#  5. 정의역·치역(domain · range)을 지킨다 → validate()가 검사
#
# 『무정』에 적용한 판단
#  - 작중 인물은 E21 Person이 아니다. E21의 범위는 '살았거나 살았다고 여겨지는 실제 사람'.
#    → 작중 인물 = mjo:Character ⊂ E89 Propositional Object ('실제 또는 상상의 것에 관한 명제들')
#      (GOLEM 온톨로지 G1 Character가 E89를 확장하는 것과 같은 방향)
#  - 작품 밖 실존 인물(예수 · 나폴레옹 · 톨스토이 · 이태백 …)은 E21 Person.
#  - 『무정』 · 장 · 문단 · 발화는 E33 Linguistic Object, 포함은 P106 is composed of, 원문은 P190 has symbolic content.
#  - 등장(MENTIONED_IN)은 P67 refers to의 방향을 뒤집은 것: (문단) P67 refers to (인물).
#  - '말한다'(SAYS)는 P14 carried out by로 쓸 수 없다: P14의 치역은 E39 Actor(실제 행위자)인데 작중 인물은 E89.
#    → 확장 mjo:has_speaker ⊂ P67 refers to (발화 텍스트가 화자를 가리킨다)
import re, json, collections
from lxml import etree
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS
from rdflib.namespace import XSD

TEI = "{http://www.tei-c.org/ns/1.0}"
XID = "{http://www.w3.org/XML/1998/namespace}id"
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
MJ = Namespace("https://github.com/ByungjunKim/Mujeong/id/")          # 임시 IRI 기준(공개 때 확정)
MJO = Namespace("https://github.com/ByungjunKim/Mujeong/ontology#")    # 우리 확장

REAL_PERSONS = {"예수", "나폴레옹", "페스탈로치", "엘렌 케이", "웰링턴", "톨스토이", "루소", "셰익스피어", "괴테", "크로포트킨",
                "타고르", "강주사마", "소동파", "두보", "이태백", "고적", "왕창령", "탁문군", "사마상여"}
OTHER_WORK = {"춘향", "이도령", "양창곡", "춘향모", "남원 부사", "아담", "에와"}

# 정의역·치역과 상위 클래스 (Erlangen CRM ecrm_current.owl에서 뽑은 값, 7.1.x와 같은 이름)
DR = {"P1_is_identified_by": ("E1_CRM_Entity", "E41_Appellation"), "P2_has_type": ("E1_CRM_Entity", "E55_Type"),
      "P3_has_note": ("E1_CRM_Entity", "Literal"), "P67_refers_to": ("E89_Propositional_Object", "E1_CRM_Entity"),
      "P72_has_language": ("E33_Linguistic_Object", "E56_Language"), "P102_has_title": ("E71_Human-Made_Thing", "E35_Title"),
      "P106_is_composed_of": ("E90_Symbolic_Object", "E90_Symbolic_Object"), "P190_has_symbolic_content": ("E90_Symbolic_Object", "Literal")}
SUPER = {
 "E18_Physical_Thing": ["E1_CRM_Entity", "E18_Physical_Thing", "E70_Thing", "E72_Legal_Object", "E77_Persistent_Item"],
 "E21_Person": ["E18_Physical_Thing", "E19_Physical_Object", "E1_CRM_Entity", "E20_Biological_Object", "E21_Person", "E39_Actor", "E70_Thing", "E72_Legal_Object", "E77_Persistent_Item"],
 "E33_Linguistic_Object": ["E1_CRM_Entity", "E28_Conceptual_Object", "E33_Linguistic_Object", "E70_Thing", "E71_Human-Made_Thing", "E72_Legal_Object", "E73_Information_Object", "E77_Persistent_Item", "E89_Propositional_Object", "E90_Symbolic_Object"],
 "E35_Title": ["E1_CRM_Entity", "E28_Conceptual_Object", "E33_Linguistic_Object", "E35_Title", "E41_Appellation", "E70_Thing", "E71_Human-Made_Thing", "E72_Legal_Object", "E73_Information_Object", "E77_Persistent_Item", "E89_Propositional_Object", "E90_Symbolic_Object"],
 "E41_Appellation": ["E1_CRM_Entity", "E28_Conceptual_Object", "E41_Appellation", "E70_Thing", "E71_Human-Made_Thing", "E72_Legal_Object", "E77_Persistent_Item", "E90_Symbolic_Object"],
 "E42_Identifier": ["E1_CRM_Entity", "E28_Conceptual_Object", "E41_Appellation", "E42_Identifier", "E70_Thing", "E71_Human-Made_Thing", "E72_Legal_Object", "E77_Persistent_Item", "E90_Symbolic_Object"],
 "E53_Place": ["E1_CRM_Entity", "E53_Place"],
 "E55_Type": ["E1_CRM_Entity", "E28_Conceptual_Object", "E55_Type", "E70_Thing", "E71_Human-Made_Thing", "E77_Persistent_Item"],
 "E56_Language": ["E1_CRM_Entity", "E28_Conceptual_Object", "E55_Type", "E56_Language", "E70_Thing", "E71_Human-Made_Thing", "E77_Persistent_Item"],
 "E74_Group": ["E1_CRM_Entity", "E39_Actor", "E74_Group", "E77_Persistent_Item"],
 "E89_Propositional_Object": ["E1_CRM_Entity", "E28_Conceptual_Object", "E70_Thing", "E71_Human-Made_Thing", "E77_Persistent_Item", "E89_Propositional_Object"],
}
EXT_CLASS = {"Character": "E89_Propositional_Object"}
EXT_PROP = {"has_speaker": "P67_refers_to", "has_addressee": "P67_refers_to"}


def text(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def ids(a):
    return [x[1:] if x.startswith("#") else x for x in (a or "").split() if x.strip()]


def to_crm(root):
    g = Graph()
    for p, n in (("crm", CRM), ("mj", MJ), ("mjo", MJO), ("rdfs", RDFS)):
        g.bind(p, n)
    # 확장 선언 (규약 4)
    g.add((MJO.Character, RDF.type, RDFS.Class)); g.add((MJO.Character, RDFS.subClassOf, CRM.E89_Propositional_Object))
    g.add((MJO.Character, RDFS.label, Literal("작중 인물", lang="ko")))
    g.add((MJO.Character, RDFS.comment, Literal("허구 세계의 인물. E21 Person(실제 인물)이 아니라 E89 Propositional Object의 하위로 둔다.", lang="ko")))
    for p, sup in EXT_PROP.items():
        g.add((MJO[p], RDF.type, RDF.Property)); g.add((MJO[p], RDFS.subPropertyOf, CRM[sup]))
        g.add((MJO[p], RDFS.domain, CRM.E33_Linguistic_Object)); g.add((MJO[p], RDFS.range, CRM.E1_CRM_Entity))
    g.add((MJO.has_speaker, RDFS.label, Literal("화자", lang="ko"))); g.add((MJO.has_addressee, RDFS.label, Literal("청자(@toWhom)", lang="ko")))
    # 유형 (규약 3)
    def T(slug, label):
        u = MJ["type/" + slug]
        if (u, RDF.type, CRM.E55_Type) not in g:
            g.add((u, RDF.type, CRM.E55_Type)); g.add((u, RDFS.label, Literal(label, lang="ko")))
        return u
    def name_nodes(ent, key, names, tei_id):
        for k, n in enumerate(names):
            a = MJ[f"appellation/{key}/{k}"]
            g.add((a, RDF.type, CRM.E41_Appellation)); g.add((a, CRM.P190_has_symbolic_content, Literal(n, lang="ko")))
            if k > 0:
                g.add((a, CRM.P2_has_type, T("alias", "별칭")))
            g.add((ent, CRM.P1_is_identified_by, a))
        i = MJ[f"identifier/{key}"]
        g.add((i, RDF.type, CRM.E42_Identifier)); g.add((i, CRM.P190_has_symbolic_content, Literal(tei_id)))
        g.add((i, CRM.P2_has_type, T("tei-xml-id", "TEI xml:id"))); g.add((ent, CRM.P1_is_identified_by, i))

    work = MJ["work/mujeong"]
    g.add((work, RDF.type, CRM.E33_Linguistic_Object)); g.add((work, RDFS.label, Literal("무정", lang="ko")))
    g.add((work, CRM.P2_has_type, T("novel", "장편소설")))
    tt = MJ["work/mujeong/title"]
    g.add((tt, RDF.type, CRM.E35_Title)); g.add((tt, CRM.P190_has_symbolic_content, Literal("무정", lang="ko"))); g.add((work, CRM.P102_has_title, tt))
    ko = MJ["language/ko"]; g.add((ko, RDF.type, CRM.E56_Language)); g.add((ko, RDFS.label, Literal("한국어", lang="ko")))
    g.add((work, CRM.P72_has_language, ko))

    # 등록부 → 개체
    ent = {}
    stats = collections.Counter()
    for tag, kind in (("person", "person"), ("personGrp", "group"), ("place", "place"), ("org", "org"), ("object", "object")):
        for el in root.iter(TEI + tag):
            i = el.get(XID)
            if not i:
                continue
            nt = {"person": "persName", "group": "persName", "place": "placeName", "org": "orgName", "object": "objectName"}[kind]
            names = ([text(n) for n in el.iter(TEI + nt)] if kind == "object" else [text(n) for n in el.findall(TEI + nt)]) or [i]
            u = MJ["entity/" + i]
            main = names[0]
            if kind in ("person", "group"):
                if main in REAL_PERSONS:
                    g.add((u, RDF.type, CRM.E21_Person)); stats["E21 실존 인물"] += 1
                else:
                    g.add((u, RDF.type, MJO.Character)); g.add((u, RDF.type, CRM.E89_Propositional_Object))
                    if main in OTHER_WORK:
                        g.add((u, CRM.P2_has_type, T("character-of-other-work", "다른 작품·경전의 인물"))); stats["작중 인물(다른 작품)"] += 1
                    elif kind == "group":
                        g.add((u, CRM.P2_has_type, T("character-group", "작중 인물 집단"))); stats["작중 인물 집단"] += 1
                    else:
                        g.add((u, CRM.P2_has_type, T("fictional-character", "『무정』 작중 인물"))); stats["『무정』 작중 인물"] += 1
            elif kind == "place":
                g.add((u, RDF.type, CRM.E53_Place)); stats["E53 장소"] += 1
            elif kind == "org":
                g.add((u, RDF.type, CRM.E74_Group)); stats["E74 집단(기관)"] += 1
            else:
                g.add((u, RDF.type, CRM.E18_Physical_Thing)); stats["E18 사물"] += 1
            g.add((u, RDFS.label, Literal(main, lang="ko")))
            name_nodes(u, i, names, i)
            note = el.find(TEI + "note")
            if note is not None and text(note):
                g.add((u, CRM.P3_has_note, Literal(text(note), lang="ko")))
            ent[i] = u
    # 본문
    body = root.find(".//" + TEI + "body")
    for d in body.findall(TEI + "div"):
        n = d.get("n")
        ch = MJ[f"text/ch{n}"]
        g.add((ch, RDF.type, CRM.E33_Linguistic_Object)); g.add((ch, RDFS.label, Literal(f"{n}장", lang="ko")))
        g.add((ch, CRM.P2_has_type, T("chapter", "장") if d.get("type") == "chapter" else T("part", "장 미분할 구간")))
        g.add((work, CRM.P106_is_composed_of, ch))
        for seq, p in enumerate(d.iter(TEI + "p", TEI + "l"), 1):
            pu = MJ[f"text/ch{n}/p{seq}"]
            g.add((pu, RDF.type, CRM.E33_Linguistic_Object)); g.add((pu, RDFS.label, Literal(f"{n}장 {seq}", lang="ko")))
            g.add((pu, CRM.P2_has_type, T("paragraph", "문단") if p.tag == TEI + "p" else T("verse-line", "시행")))
            g.add((pu, CRM.P190_has_symbolic_content, Literal(text(p), lang="ko")))
            g.add((ch, CRM.P106_is_composed_of, pu))
            for el in p.iter(TEI + "persName", TEI + "rs", TEI + "placeName", TEI + "orgName", TEI + "objectName"):
                for i in ids(el.get("ref")):
                    if i in ent:
                        g.add((pu, CRM.P67_refers_to, ent[i]))
            for k, s in enumerate(p.iter(TEI + "said"), 1):
                uu = MJ[f"text/ch{n}/p{seq}/u{k}"]
                g.add((uu, RDF.type, CRM.E33_Linguistic_Object))
                g.add((uu, CRM.P2_has_type, T("inner-speech", "속마음(aloud=false)") if s.get("aloud") == "false" else T("utterance", "발화")))
                g.add((uu, CRM.P190_has_symbolic_content, Literal(text(s), lang="ko")))
                g.add((pu, CRM.P106_is_composed_of, uu))
                for w in ids(s.get("who")):
                    if w in ent:
                        g.add((uu, MJO.has_speaker, ent[w]))
                for t in ids(s.get("toWhom")):
                    if t in ent:
                        g.add((uu, MJO.has_addressee, ent[t]))
                for el in s.iter(TEI + "persName", TEI + "rs"):
                    for i in ids(el.get("ref")):
                        if i in ent:
                            g.add((uu, CRM.P67_refers_to, ent[i]))
    return g, dict(stats)


def validate(g):
    """규약 5: 정의역·치역 검사. 주어·목적어의 rdf:type(확장 클래스는 상위 CRM 클래스로)이 허용 범위 안인가."""
    def classes(node):
        out = set()
        for t in g.objects(node, RDF.type):
            s = str(t)
            if s.startswith(str(CRM)):
                out.update(SUPER.get(s[len(str(CRM)):], [s[len(str(CRM)):]]))
            elif s.startswith(str(MJO)):
                out.update(SUPER[EXT_CLASS[s[len(str(MJO)):]]])
        return out
    bad = collections.Counter(); checked = collections.Counter(); ex = {}
    for s, p, o in g:
        ps = str(p)
        if ps.startswith(str(CRM)):
            key = ps[len(str(CRM)):]
        elif ps.startswith(str(MJO)) and ps[len(str(MJO)):] in EXT_PROP:
            key = EXT_PROP[ps[len(str(MJO)):]]
            key2 = "E33_Linguistic_Object"
        else:
            continue
        if key not in DR:
            bad["표에 없는 속성 " + key] += 1; continue
        dom, rng = DR[key]
        if ps.startswith(str(MJO)):
            dom = "E33_Linguistic_Object"
        checked[ps.rsplit("/", 1)[-1].split("#")[-1]] += 1
        if dom not in classes(s):
            bad[f"{key} 정의역 위반"] += 1; ex.setdefault(f"{key} 정의역 위반", str(s))
        if rng == "Literal":
            if not isinstance(o, Literal):
                bad[f"{key} 치역 위반"] += 1
        elif rng not in classes(o):
            bad[f"{key} 치역 위반"] += 1; ex.setdefault(f"{key} 치역 위반", f"{s} → {o}")
    return {"검사한 트리플": dict(checked), "위반": dict(bad), "위반 예": ex}


if __name__ == "__main__":
    import sys
    root = etree.parse(sys.argv[1]).getroot()
    g, stats = to_crm(root)
    g.serialize(sys.argv[2], format="turtle")
    rep = {"트리플": len(g), "개체 분류": stats, "검증": validate(g)}
    json.dump(rep, open(sys.argv[2].rsplit(".", 1)[0] + "_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
