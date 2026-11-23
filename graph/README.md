# graph/ — 『무정』 그래프 데이터

통합 TEI에서 만든 속성 그래프다. 판마다 폴더를 따로 둔다.

| 판 | 저본 | 만든 날 | 노드 | 관계 |
|---|---|---|---|---|
| [`v1/`](v1/) | `merged/무정_통합본_v1.xml` (2026-11-23 동결, 커밋 bb9ea39) | 2026-11-23 | 4,468 | 16,576 |

## v1/ 의 파일
| 파일 | 내용 |
|---|---|
| `nodes_Person.csv` 등 7개 | 노드. Person 168 · Place 138 · Org 41 · Object 4 · Chapter 126 · Paragraph 2,037(원문 글 포함) · Utterance 1,954 |
| `rels_*.csv` 10개 | 관계. 파일 이름이 `rels_관계_시작라벨_끝라벨.csv`이고 `start` · `end` 열이 양 끝 노드의 id |
| `load_neo4j.cypher` | Neo4j 5 · AuraDB에서 위 CSV를 이 저장소 주소로 바로 읽어 적재하는 Cypher |
| `report.json` · `MANIFEST.json` | 변환 보고와 저본 정보(sha256 · 커밋 · 개수 · 알려진 문제) |
| `crm/mujeong_crm_v1.ttl` | 같은 내용을 CIDOC CRM 7.1 어휘로 적은 RDF(Turtle, 트리플 30,513개). 작중 인물은 `mjo:Character` ⊂ E89. 이름공간 IRI는 임시 |

## 스키마
```
(Paragraph)-[:IN]->(Chapter)
(Person|Place|Org|Object)-[:MENTIONED_IN {surface, tag}]->(Paragraph)
(Person)-[:SAYS]->(Utterance)        소리 내어 한 말 (said, aloud가 false가 아님)
(Person)-[:THINKS]->(Utterance)      속마음 (said aloud="false")
(Utterance)-[:IN]->(Paragraph)
(Utterance)-[:REFERS_TO {surface}]->(Person)   말 속에서 가리킨 인물
```
- 노드 속성: Person(id · name · aliases · kind · sex · cert) / Chapter(id · n · type · order · title · source · resp) / Paragraph(id · chapter · seq · order · text) / Utterance(id · text · aloud · direct · chapter · paragraph · who)
- '함께 등장'은 저장하지 않는다. 같은 문단을 공유하는지로 질의할 때 계산한다.
- `said/@who`가 기관을 가리키는 2곳(22 · 25장, 동맹)은 `rels_SAYS_Org_Utterance.csv`에 있다.
- Paragraph는 통합본의 `<p>` · `<l>`이다. v1에는 원문 한 문단을 여러 `<p>`로 나눈 곳이 있어(16 · 17 · 19 · 116장) 저본 문단 수(1,977)보다 많다. `merged/기록/v1_최종검수_2026-11-23.md` 참조.

## 다시 만들기
```
python merged/tools/tei2graph.py merged/무정_통합본_v2.xml graph/v2
python merged/tools/tei2crm.py   merged/무정_통합본_v2.xml graph/v2/crm/mujeong_crm_v2.ttl   # rdflib 필요
```
